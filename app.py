from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date
from decimal import Decimal
import os

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

def get_product(code):
    rows = query('SELECT * FROM products WHERE code=%s', (code,), True)
    return rows[0] if rows else None

def get_recipe(code):
    rows = query('SELECT * FROM recipes WHERE code=%s', (code,), True)
    return rows[0] if rows else None

def notifications():
    products = query('SELECT * FROM products ORDER BY expiry_date IS NULL, expiry_date ASC, name', fetch=True)
    today = date.today(); result = []
    for p in products:
        qty = float(p['quantity'])
        if qty <= 2:
            result.append({'type':'critical','icon':'!','title':'Estoque crítico','text':f"{p['name']} está com apenas {qty:g} {p['unit']}.",'code':p['code']})
        elif qty <= 5:
            result.append({'type':'low','icon':'↓','title':'Estoque baixo','text':f"{p['name']} está com {qty:g} {p['unit']}.",'code':p['code']})
        if p['expiry_date']:
            days = (p['expiry_date'] - today).days
            if days < 0:
                result.append({'type':'expired','icon':'×','title':'Produto vencido','text':f"{p['name']} venceu em {p['expiry_date'].strftime('%d/%m/%Y')}.",'code':p['code']})
            elif days == 0:
                result.append({'type':'expiry','icon':'!','title':'Validade vence hoje','text':f"{p['name']} vence hoje.",'code':p['code']})
            elif days <= 7:
                result.append({'type':'expiry','icon':'!','title':'Validade próxima','text':f"{p['name']} vence em {days} dia(s).",'code':p['code']})
    return result

def notification_count(): return len(notifications())

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

@app.route('/users/new', methods=['GET', 'POST'])
@login_required
def create_user():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('As senhas não coincidem.', 'error')
            return redirect(url_for('create_user'))

        existing_user = query(
            'SELECT * FROM users WHERE email=%s',
            (email,),
            True
        )

        if existing_user:
            flash('Já existe um usuário com esse e-mail.', 'error')
            return redirect(url_for('create_user'))

        password_hash = generate_password_hash(password)

        query(
            '''
            INSERT INTO users (name, email, password_hash)
            VALUES (%s, %s, %s)
            ''',
            (name, email, password_hash)
        )

        flash('Usuário cadastrado com sucesso!', 'success')
        return redirect(url_for('create_user'))

    return render_template('user_form.html')

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

@app.route('/products/new', methods=['GET','POST'])
@login_required
def create_product():
    if request.method == 'POST':
        code=request.form['code'].strip().upper()
        try:
            query('INSERT INTO products(code,name,quantity,unit,expiry_date) VALUES(%s,%s,%s,%s,%s)', (code,request.form['name'].strip(),request.form['quantity'],request.form['unit'],request.form['expiry_date'] or None))
            flash(f'Cadastro completo com sucesso! Código do produto: {code}','success'); return redirect(url_for('create_product'))
        except Error as e: flash('Já existe um produto com esse código.' if e.errno==1062 else str(e),'error')
    return render_template('product_form.html')

@app.route('/products/edit', methods=['GET','POST'])
@login_required
def edit_product():
    code=(request.args.get('code','') if request.method=='GET' else request.form.get('code','')).strip().upper(); product=get_product(code) if code else None
    if request.method=='POST':
        if not product: flash('Produto não encontrado.','error'); return redirect(url_for('edit_product'))
        query('UPDATE products SET quantity=%s,unit=%s,expiry_date=%s WHERE code=%s',(request.form['quantity'],request.form['unit'],request.form['expiry_date'] or None,code))
        flash('Edição completa com sucesso!','success'); return redirect(url_for('edit_product',code=code))
    return render_template('edit.html', product=product, searched=bool(code))

@app.route('/products/delete', methods=['GET','POST'])
@login_required
def delete_product():
    code=(request.args.get('code','') if request.method=='GET' else request.form.get('code','')).strip().upper(); product=get_product(code) if code else None
    if request.method=='POST':
        if not product: flash('Produto não encontrado.','error'); return redirect(url_for('delete_product'))
        query('DELETE FROM products WHERE code=%s',(code,)); flash('Exclusão completa com sucesso!','success'); return redirect(url_for('delete_product'))
    return render_template('delete.html', product=product, searched=bool(code))

@app.route('/notifications')
@login_required
def notification_page(): return render_template('notifications.html', notifications=notifications())

@app.route('/recipes')
@login_required
def recipes():
    rows=query('SELECT * FROM recipes ORDER BY name',fetch=True); view=[]
    for r in rows:
        ings=query('SELECT ri.*,p.name product_name,p.quantity stock_quantity,p.unit stock_unit FROM recipe_ingredients ri LEFT JOIN products p ON p.code=ri.product_code WHERE ri.recipe_id=%s ORDER BY p.name',(r['id'],),True)
        missing=[]
        for ing in ings:
            if not ing['product_name']: missing.append(ing['product_code']); continue
            if ing['unit']!=ing['stock_unit'] or Decimal(str(ing['stock_quantity'])) < Decimal(str(ing['quantity'])): missing.append(ing['product_name'])
        r['ingredients']=ings; r['missing']=missing; r['available']=bool(ings) and not missing; view.append(r)
    return render_template('recipes.html', recipes=view)

@app.route('/recipes/new', methods=['GET','POST'])
@login_required
def create_recipe():
    products=query('SELECT code,name,unit,quantity FROM products ORDER BY name',fetch=True)
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
    products=query('SELECT code,name,unit,quantity FROM products ORDER BY name',fetch=True)
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

@app.route('/api/notifications')
@login_required
def api_notifications(): return jsonify(notifications())

if __name__=='__main__': app.run(host='0.0.0.0',port=5000,debug=True)
