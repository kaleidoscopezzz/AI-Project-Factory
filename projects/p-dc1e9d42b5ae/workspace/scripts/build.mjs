import {mkdir,copyFile,readFile} from 'node:fs/promises';
import {Script} from 'node:vm';
new Script(await readFile('src/web/app.js','utf8'));
for(const f of ['contracts/index.mjs','domain/books.mjs','adapters/store.mjs','server/server.mjs'])await import('../src/'+f);
await mkdir('dist',{recursive:true});for(const f of ['index.html','style.css','app.js'])await copyFile('src/web/'+f,'dist/'+f);console.log('Build passed: 3 local dist assets');
