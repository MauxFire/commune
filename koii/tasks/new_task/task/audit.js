```javascript
const { namespaceWrapper } = require("@_koii/namespace-wrapper");

class Audit {
  async validateNode(submissionValue, round) {
    try {
      const num1 = 5;
      const num2 = 7;
      const expectedSum = num1 + num2;
      return submissionValue == expectedSum;
    } catch (e) {
      console.log("Error in validate:", e);
      return false;
    }
  }

  async auditTask(roundNumber) {
    console.log("AuditTask called with round", roundNumber);
    console.log(
      await namespaceWrapper.getSlot(),
      "Current slot while calling auditTask"
    );
    await namespaceWrapper.validateAndVoteOnNodes(
      this.validateNode,
      roundNumber
    );
  }
}

const audit = new Audit();
module.exports = { audit };
```

