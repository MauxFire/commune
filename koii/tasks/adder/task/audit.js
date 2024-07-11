const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Audit {
  async validateNode(submissionValue, round) {
    try {
      const num1 = parseInt(await namespaceWrapper.storeGet('num1'));
      const num2 = parseInt(await namespaceWrapper.storeGet('num2'));
      const expectedResult = num1 + num2;
      return parseInt(submissionValue) === expectedResult;
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

