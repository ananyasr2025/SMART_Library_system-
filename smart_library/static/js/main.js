// Confirm before delete; auto-hide flash alerts
document.querySelectorAll('form[data-confirm]').forEach(f=>f.addEventListener('submit',e=>{if(!confirm(f.dataset.confirm))e.preventDefault()}));
setTimeout(()=>document.querySelectorAll('.alert').forEach(a=>a.remove()),5000);
