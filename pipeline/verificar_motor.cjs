// Ejecución sin navegador: Node.js 18+; sin dependencias adicionales.
const fs = require('node:fs');
require('../gui/motor.js');
const D = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const escenarios = JSON.parse(fs.readFileSync(0, 'utf8'));
const modelo = new MicroSim.Modelo(D);
process.stdout.write(JSON.stringify(escenarios.map(e => {
  try { return {resultado: modelo.simular(e)}; }
  catch (err) { return {error: err.message}; }
})));
