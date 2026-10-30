from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date
from decimal import Decimal
import os
import uuid

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'arb-estoque-inteligente-local')

DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'estoque_inteligente'),
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def query(sql, params=(), fetch=False):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        if fetch: return cur.fetchall()
        conn.commit(); return cur.lastrowid
    finally:
        cur.close(); conn.close()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped

def get_product(product_id):
    rows = query(
        'SELECT * FROM products WHERE id=%s',
        (product_id,),
        True
    )
    return rows[0] if rows else None

def get_recipe(code):
    rows = query('SELECT * FROM recipes WHERE code=%s', (code,), True)
    return rows[0] if rows else None

def notifications():
    user_id = session.get('user_id')
    if not user_id: return []
    products = query('SELECT * FROM products ORDER BY expiry_date IS NULL, expiry_date ASC, name', fetch=True)
    today = date.today(); result = []
    for p in products:
        qty = float(p['quantity'])
        if qty <= 2:
            result.append({'key':f"stock-critical:{p['code']}",'type':'critical','icon':'!','title':'Estoque crítico','text':f"{p['name']} está com apenas {qty:g} {p['unit']}.",'code':p['code']})
        elif qty <= 5:
            result.append({'key':f"stock-low:{p['code']}",'type':'low','icon':'↓','title':'Estoque baixo','text':f"{p['name']} está com {qty:g} {p['unit']}.",'code':p['code']})
        if p['expiry_date']:
            days = (p['expiry_date'] - today).days
            if days < 0:
                result.append({'key':f"expired:{p['code']}",'type':'expired','icon':'×','title':'ingrediente vencido','text':f"{p['name']} venceu em {p['expiry_date'].strftime('%d/%m/%Y')}.",'code':p['code']})
            elif days == 0:
                result.append({'key':f"expiry-today:{p['code']}",'type':'expiry','icon':'!','title':'Validade vence hoje','text':f"{p['name']} vence hoje.",'code':p['code']})
            elif days <= 7:
                result.append({'key':f"expiry-soon:{p['code']}",'type':'expiry','icon':'!','title':'Validade próxima','text':f"{p['name']} vence em {days} dia(s).",'code':p['code']})
    read_rows = query('SELECT notification_key FROM notification_reads WHERE user_id=%s', (user_id,), True)
    read_keys = {row['notification_key'] for row in read_rows}
    for notification in result:
        notification['is_read'] = notification['key'] in read_keys
    return result

def notification_count(): return sum(not n['is_read'] for n in notifications())

@app.context_processor
def global_data(): return {'notification_count': notification_count, 'brand_name':'ARB Estoque Inteligente'}

@app.route('/')
def index(): return redirect(url_for('home') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        users = query(
            'SELECT * FROM users WHERE email=%s',
            (email,),
            True
        )

        if users and check_password_hash(users[0]['password_hash'], password):
            session['user_id'] = users[0]['id']
            session['user_name'] = users[0]['name']
            return redirect(url_for('home'))

        flash('E-mail ou senha incorretos.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    p = query('SELECT COUNT(*) total FROM products', fetch=True)[0]['total']
    r = query('SELECT COUNT(*) total FROM recipes', fetch=True)[0]['total']
    return render_template('home.html', total_products=p, total_recipes=r, alerts=notification_count())

@app.route('/products')
@login_required
def products(): return render_template('catalog.html', products=query('SELECT * FROM products ORDER BY name', fetch=True))

@app.route('/products/new', methods=['GET', 'POST'])
@login_required
def create_product():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        brand = request.form.get('brand', '').strip()

        if not name or not brand:
            flash('Informe o nome do ingrediente e a marca.', 'error')
            return render_template('product_form.html')

        # Código interno gerado automaticamente para manter os vínculos com receitas.
        code = uuid.uuid4().hex[:24].upper()

        try:
            query(
                'INSERT INTO products(code, name, brand, quantity, unit, expiry_date) '
                'VALUES(%s, %s, %s, %s, %s, %s)',
                (
                    code,
                    name,
                    brand,
                    request.form['quantity'],
                    request.form['unit'],
                    request.form.get('expiry_date') or None
                )
            )
            flash('Ingrediente cadastrado com sucesso!', 'success')
            return redirect(url_for('create_product'))
        except Error as e:
            flash(
                'Não foi possível cadastrar o ingrediente. Confira os dados e tente novamente.'
                if e.errno == 1062 else str(e),
                'error'
            )

    return render_template('product_form.html')
@app.route('/products/edit', methods=['GET', 'POST'])
@login_required
def edit_product():
    raw_id = (
        request.form.get('product_id', '')
        if request.method == 'POST'
        else request.args.get('product_id', '')
    ).strip()

    product_id = int(raw_id) if raw_id.isdigit() else None
    product = get_product(product_id) if product_id else None

    products = query(
        'SELECT id, name, brand, quantity, unit FROM products ORDER BY name, brand',
        fetch=True
    )

    if request.method == 'POST':
        if not product:
            flash('Ingrediente não encontrado.', 'error')
            return redirect(url_for('edit_product'))

        name = request.form.get('name', '').strip()
        brand = request.form.get('brand', '').strip()

        if not name or not brand:
            flash('Informe o nome do ingrediente e a marca.', 'error')
            return redirect(url_for('edit_product', product_id=product_id))

        query(
            'UPDATE products SET name=%s, brand=%s, quantity=%s, unit=%s, expiry_date=%s WHERE id=%s',
            (
                name,
                brand,
                request.form['quantity'],
                request.form['unit'],
                request.form.get('expiry_date') or None,
                product_id
            )
        )

        flash('Ingrediente atualizado com sucesso!', 'success')
        return redirect(url_for('edit_product', product_id=product_id))

    return render_template(
        'edit.html',
        product=product,
        products=products,
        searched=bool(raw_id)
    )

@app.route('/products/delete', methods=['GET', 'POST'])
@login_required
def delete_product():
    raw_id = (
        request.form.get('product_id', '')
        if request.method == 'POST'
        else request.args.get('product_id', '')
    ).strip()

    product_id = int(raw_id) if raw_id.isdigit() else None
    product = get_product(product_id) if product_id else None

    products = query(
        'SELECT id, name, brand, quantity, unit FROM products ORDER BY name, brand',
        fetch=True
    )

    if request.method == 'POST':
        if not product:
            flash('Ingrediente não encontrado.', 'error')
            return redirect(url_for('delete_product'))

        query('DELETE FROM products WHERE id=%s', (product_id,))
        flash('Ingrediente excluído com sucesso!', 'success')
        return redirect(url_for('delete_product'))

    return render_template(
        'delete.html',
        product=product,
        products=products,
        searched=bool(raw_id)
    )

@app.route('/notifications')
@login_required
def notification_page(): return render_template('notifications.html', notifications=notifications())

@app.route('/notifications/read', methods=['POST'])
@login_required
def mark_notification_read():
    notification_key = request.form.get('notification_key', '').strip()
    active_keys = {n['key'] for n in notifications()}
    if notification_key and notification_key in active_keys:
        query('INSERT INTO notification_reads (user_id, notification_key) VALUES (%s, %s) ON DUPLICATE KEY UPDATE read_at=CURRENT_TIMESTAMP', (session['user_id'], notification_key))
    return redirect(url_for('notification_page'))

@app.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    for notification in notifications():
        query('INSERT INTO notification_reads (user_id, notification_key) VALUES (%s, %s) ON DUPLICATE KEY UPDATE read_at=CURRENT_TIMESTAMP', (session['user_id'], notification['key']))
    return redirect(url_for('notification_page'))

@app.route('/recipes')
@login_required
def recipes():
    rows=query('SELECT * FROM recipes ORDER BY name',fetch=True); view=[]
    for r in rows:
        ings=query('SELECT ri.*,p.name product_name,p.brand product_brand,p.quantity stock_quantity,p.unit stock_unit FROM recipe_ingredients ri LEFT JOIN products p ON p.code=ri.product_code WHERE ri.recipe_id=%s ORDER BY p.name,p.brand',(r['id'],),True)     
        for ing in ings:
            if not ing['product_name']: missing.append(ing['product_code']); continue
            if ing['unit']!=ing['stock_unit'] or Decimal(str(ing['stock_quantity'])) < Decimal(str(ing['quantity'])): missing.append(ing['product_name'])
        r['ingredients']=ings; r['missing']=missing; r['available']=bool(ings) and not missing; view.append(r)
    return render_template('recipes.html', recipes=view)

@app.route('/recipes/new', methods=['GET','POST'])
@login_required
def create_recipe():
    products=query('SELECT code,name,brand,unit,quantity FROM products ORDER BY name,brand',fetch=True)
    if request.method=='POST':
        code=request.form['code'].strip().upper()
        try:
            rid=query('INSERT INTO recipes(code,name,yield_text,preparation_time,instructions) VALUES(%s,%s,%s,%s,%s)',(code,request.form['name'].strip(),request.form.get('yield_text') or None,request.form.get('preparation_time') or None,request.form.get('instructions') or None))
            for pc,qty,unit in zip(request.form.getlist('ingredient_product[]'),request.form.getlist('ingredient_quantity[]'),request.form.getlist('ingredient_unit[]')):
                if pc and qty: query('INSERT INTO recipe_ingredients(recipe_id,product_code,quantity,unit) VALUES(%s,%s,%s,%s)',(rid,pc,qty,unit))
            flash(f'Receita cadastrada com sucesso! Código: {code}','success'); return redirect(url_for('create_recipe'))
        except Error as e: flash('Já existe uma receita com esse código.' if e.errno==1062 else str(e),'error')
    return render_template('recipe_form.html', products=products)

@app.route('/recipes/edit', methods=['GET','POST'])
@login_required
def edit_recipe():
    products=query('SELECT code,name,brand,unit,quantity FROM products ORDER BY name,brand',fetch=True)
    code=(request.args.get('code','') if request.method=='GET' else request.form.get('code','')).strip().upper(); recipe=get_recipe(code) if code else None
    if request.method=='POST':
        if not recipe: flash('Receita não encontrada.','error'); return redirect(url_for('edit_recipe'))
        query('UPDATE recipes SET name=%s,yield_text=%s,preparation_time=%s,instructions=%s WHERE code=%s',(request.form['name'].strip(),request.form.get('yield_text') or None,request.form.get('preparation_time') or None,request.form.get('instructions') or None,code))
        query('DELETE FROM recipe_ingredients WHERE recipe_id=%s',(recipe['id'],))
        for pc,qty,unit in zip(request.form.getlist('ingredient_product[]'),request.form.getlist('ingredient_quantity[]'),request.form.getlist('ingredient_unit[]')):
            if pc and qty: query('INSERT INTO recipe_ingredients(recipe_id,product_code,quantity,unit) VALUES(%s,%s,%s,%s)',(recipe['id'],pc,qty,unit))
        flash('Receita editada com sucesso!','success'); return redirect(url_for('edit_recipe',code=code))
    ingredients=query('SELECT * FROM recipe_ingredients WHERE recipe_id=%s ORDER BY id',(recipe['id'],),True) if recipe else []
    return render_template('recipe_edit.html', products=products, recipe=recipe, ingredients=ingredients, searched=bool(code))

@app.route('/recipes/delete', methods=['POST'])
@login_required
def delete_recipe():
    code = request.form.get('code', '').strip().upper()
    recipe = get_recipe(code) if code else None

    if not recipe:
        flash('Receita não encontrada.', 'error')
    else:
        query('DELETE FROM recipes WHERE id=%s', (recipe['id'],))
        flash('Receita excluída com sucesso!', 'success')

    return redirect(url_for('recipes'))

@app.route('/api/notifications')
@login_required
def api_notifications(): return jsonify(notifications())

if __name__=='__main__': app.run(host='0.0.0.0',port=5000,debug=True)
