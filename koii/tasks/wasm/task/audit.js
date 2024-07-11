const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Audit {
  async validateNode(submission_value, round) {
    let vote;
    console.log('SUBMISSION VALUE', submission_value, round);
    try {
      // Verify the WASM result
      // This is a placeholder validation. You should implement your own validation logic.
      if (typeof submission_value === 'number' && submission_value > 0) {
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

