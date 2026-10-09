import {spawnSync} from 'node:child_process';
const r=spawnSync(process.execPath,['--test','--test-concurrency=1','tests/goal0.test.mjs'],{stdio:'inherit',timeout:175000});if(r.error)console.error(r.error.message);process.exitCode=r.status??1;
