
const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Audit {
  async validateNode(submission_value, round) {
    let vote;
    console.log('SUBMISSION VALUE', submission_value, round);
    try {
      const [expression, result] = submission_value.split('=');
      const [num1, num2] = expression.split('+').map(Number);
      const expectedSum = num1 + num2;
      
      if (expectedSum === Number(result)) {
        vote = true;
      } else {
        vote = false;
      }
    } catch (e) {
      console.error(e);
      vote = false;
    }
    return vote;
  }

  async auditTask(roundNumber) {
    console.log('AUDIT CALLED IN ROUND', roundNumber);
    console.log('CURRENT SLOT IN AUDIT', await namespaceWrapper.getSlot());
    await namespaceWrapper.validateAndVoteOnNodes(this.validateNode, roundNumber);
  }
}

const audit = new Audit();
module.exports = { audit };

