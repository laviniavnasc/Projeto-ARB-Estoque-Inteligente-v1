
function toggleSidebar(){
  const sidebar = document.getElementById("sidebar");
  if(sidebar) sidebar.classList.toggle("open");
}

function togglePassword(){
  const input = document.querySelector('input[name="password"]');
  if(!input) return;
  input.type = input.type === "password" ? "text" : "password";
}

document.addEventListener("click", (event) => {
  const sidebar = document.getElementById("sidebar");
  const menu = document.querySelector(".menu-btn");
  if(sidebar && sidebar.classList.contains("open") && !sidebar.contains(event.target) && event.target !== menu){
    sidebar.classList.remove("open");
  }
});

setTimeout(() => {
  document.querySelectorAll(".flash").forEach(el => {
    el.style.transition = "opacity .4s, transform .4s";
    el.style.opacity = "0";
    el.style.transform = "translateY(-5px)";
    setTimeout(() => el.remove(), 450);
  });
}, 4500);

function addIngredientRow(){
  const c=document.getElementById('ingredientRows'); if(!c) return;
  let first=c.querySelector('.ingredient-row');
  if(!first){ return; }
  const row=first.cloneNode(true);
  row.querySelectorAll('input').forEach(i=>i.value='');
  row.querySelectorAll('select').forEach(s=>s.selectedIndex=0);
  c.appendChild(row);
}
function removeIngredientRow(btn){
  const c=document.getElementById('ingredientRows'); if(!c) return;
  const rows=c.querySelectorAll('.ingredient-row');
  if(rows.length<=1){rows[0].querySelectorAll('input').forEach(i=>i.value='');rows[0].querySelectorAll('select').forEach(s=>s.selectedIndex=0);return;}
  btn.closest('.ingredient-row').remove();
}
document.addEventListener('change',e=>{
  if(e.target.matches('select[name="ingredient_product[]"]')){
    const unit=e.target.selectedOptions[0]?.dataset?.unit;
    if(unit){const s=e.target.closest('.ingredient-row').querySelector('select[name="ingredient_unit[]"]'); if(s) s.value=unit;}
  }
});
