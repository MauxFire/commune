```javascript
const { namespaceWrapper } = require("@_koii/namespace-wrapper");

class Submission {
  constructor() {}

  async task(round) {
    try {
      console.log("Task called with round", round);
      const num1 = 5;
      const num2 = 7;
      const sum = num1 + num2;
      await namespaceWrapper.storeSet("sum", sum);
      return "Done";
    } catch (err) {
      console.error("ERROR IN EXECUTING TASK", err);
      return "ERROR IN EXECUTING TASK" + err;
    }
  }

  async submitTask(roundNumber) {
    console.log("SubmitTask called with round", roundNumber);
    try {
      const submission = await this.fetchSubmission(roundNumber);
      console.log("SUBMISSION", submission);
      await namespaceWrapper.checkSubmissionAndUpdateRound(
        submission,
        roundNumber
      );
      console.log("After the submission call");
    } catch (error) {
      console.log("Error in submission", error);
    }
  }

  async fetchSubmission(round) {
    console.log("FetchSubmission called with round", round);
    const sum = await namespaceWrapper.storeGet("sum");
    console.log("Sum", sum);
    return sum;
  }
}

const submission = new Submission();
module.exports = { submission };
```

