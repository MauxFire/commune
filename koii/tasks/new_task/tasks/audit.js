
const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Audit {
  async validateNode(submissionValue, round) {
    try {
      // In a real scenario, you might want to recalculate the result here
      // and compare it with the submitted value
      const num1 = 5;
      const num2 = 7;
      const expectedResult = (num1 + num2).toString();
      return submissionValue === expectedResult;
    } catch (e) {
      console.log('Error in validate:', e);
      return false;
    }
  }

  async auditTask(roundNumber) {
    console.log('auditTask called with round', roundNumber);
    console.log(
      await namespaceWrapper.getSlot(),
      'current slot while calling auditTask',
    );
    await namespaceWrapper.validateAndVoteOnNodes(
      this.validateNode,
      roundNumber,
    );
  }
}

const audit = new Audit();
module.exports = { audit };

