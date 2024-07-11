
const { namespaceWrapper } = require('@_koii/namespace-wrapper');
const { execSync } = require('child_process');
const fs = require('fs');

class Submission {
  async task(round) {
    try {
      console.log('Task called with round', round);
      
      // Run PyTorch model
      console.log('Running PyTorch model...');
      execSync('python3 pytorch_model.py');
      
      // Convert model to WASM
      console.log('Converting model to WASM...');
      execSync('python3 convert_to_wasm.py');
      
      // Read WASM file
      const wasmBuffer = fs.readFileSync('model.wasm');
      const wasmBase64 = wasmBuffer.toString('base64');
      
      // Store WASM data
      await namespaceWrapper.storeSet('wasm_model', wasmBase64);
      
      return 'Model converted to WASM successfully';
    } catch (err) {
      console.error('ERROR IN EXECUTING TASK', err);
      return 'ERROR IN EXECUTING TASK: ' + err;
    }
  }

  async submitTask(roundNumber) {
    console.log('SubmitTask called with round', roundNumber);
    try {
      const wasmBase64 = await namespaceWrapper.storeGet('wasm_model');
      console.log('SUBMISSION', wasmBase64.slice(0, 50) + '...');
      await namespaceWrapper.submitTask(wasmBase64, roundNumber);
    } catch (error) {
      console.log('Error in submission', error);
    }
  }
}

const submission = new Submission();
module.exports = { submission };
