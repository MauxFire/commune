
const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Audit {
  async validateNode(submissionValue, round) {
    try {
      // In a real-world scenario, you would load the WASM module and run some tests
      // For this example, we'll just check if the submission is a non-empty base64 string
      const isBase64 = /^[A-Za-z0-9+/]+=*$/.test(submissionValue);
      return isBase64 && submissionValue.length > 0;
    } catch (e) {
      console.log('Error in validate:', e);
      return false;
    }
  }

  async auditTask(roundNumber) {
    console.log('AuditTask called with round', roundNumber);
    await namespaceWrapper.validateAndVoteOnNodes(this.validateNode, roundNumber);
  }
}

const audit = new Audit();
module.exports = { audit };
