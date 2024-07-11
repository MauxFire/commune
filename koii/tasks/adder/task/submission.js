const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Submission {
  async task(round) {
    try {
      console.log('Task called with round', round);
      const num1 = Math.floor(Math.random() * 100);
      const num2 = Math.floor(Math.random() * 100);
      const result = num1 + num2;
      
      await namespaceWrapper.storeSet('num1', num1.toString());
      await namespaceWrapper.storeSet('num2', num2.toString());
      await namespaceWrapper.storeSet('result', result.toString());
      
      return 'Addition completed';
    } catch (err) {
      console.error('ERROR IN EXECUTING TASK', err);
      return 'ERROR IN EXECUTING TASK: ' + err;
    }
  }

  async submitTask(roundNumber) {
    console.log('SubmitTask called with round', roundNumber);
    try {
      const result = await namespaceWrapper.storeGet('result');
      console.log('SUBMISSION', result);
      await namespaceWrapper.submitTask(result, roundNumber);
    } catch (error) {
      console.log('Error in submission', error);
    }
  }
}

const submission = new Submission();
module.exports = { submission };

