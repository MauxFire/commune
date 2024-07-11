const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Submission {
  async task(round) {
    try {
      console.log('ROUND', round);
      
      // Load and run WASM blob
      const wasmModule = await WebAssembly.instantiateStreaming(fetch('path/to/your/wasm/file.wasm'));
      const result = wasmModule.instance.exports.main();
      
      // Store the result in NeDB
      if (result) {
        await namespaceWrapper.storeSet('wasmResult', result);
      }
      
      return result;
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
    const value = await namespaceWrapper.storeGet('wasmResult');
    return value;
  }
}

const submission = new Submission();
module.exports = { submission };

