const fs=require('fs'), katex=require(process.env.KATEX_PATH || 'katex');
const src=fs.readFileSync('/home/user/First-one/cheatsheet-src.html','utf8');
let errs=0;
const body=src.replace(/\$([^$]+)\$/g,(m,tex)=>{try{return katex.renderToString(tex,{throwOnError:true})}catch(e){errs++;console.error('ERR',tex,e.message);return m}});
const local='file://'+__dirname+'/node_modules/katex/dist/katex.min.css';
fs.writeFileSync(__dirname+'/print.html',body.replace('KATEX_CSS',local));
fs.writeFileSync('/home/user/First-one/econ385-exam1-cheatsheet.html',body.replace('KATEX_CSS','https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/katex.min.css'));
console.log('errors',errs);
