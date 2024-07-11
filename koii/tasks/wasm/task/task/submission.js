
const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Submission {
  async task(round) {
    try {
      console.log('ROUND', round);
      
      // Load the WASM module
      const wasmModule = await WebAssembly.instantiateStreaming(fetch('simple.wasm'));
      const { add } = wasmModule.instance.exports;

      // Use the WASM function
      const result = add(5, 3);
      const value = `WASM result: ${result}`;

      // Store the result in NeDB
      if (value) {
        await namespaceWrapper.storeSet('value', value);
      }
      
      return value;
    } catch (err) {
      console.log('ERROR IN EXECUTING TASK', err);
      return 'ERROR IN EXECUTING TASK' + err;
    }
  }

  async submitTask(round) {
    console.log('SUBMIT TASK CALLED ROUND NUMBER', round);
    try {
      console.log('SUBMIT TASK SLOT', await namespaceWrapper.getSlot());
      const submission = await this.fetchSubmission(round);
      console.log('SUBMISSION', submission);
      await namespaceWrapper.checkSubmissionAndUpdateRound(submission, round);
      console.log('SUBMISSION CHECKED AND ROUND UPDATED');
      return submission;
    } catch (error) {
      console.log('ERROR IN SUBMISSION', error);
    }
  }

  async fetchSubmission(round) {
    console.log('FETCH SUBMISSION');
    const value = await namespaceWrapper.storeGet('value');
    return value;
  }
}

const submission = new Submission();
module.exports = { submission };
