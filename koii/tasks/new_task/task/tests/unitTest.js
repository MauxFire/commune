```javascript
const { coreLogic } = require("../coreLogic");

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function executeTasks() {
  for (let i = 0; i < 10; i++) {
    let delay = 6000;
    let round = i;
    
    console.log(`Executing task for round ${round}`);
    await coreLogic.task(round);
    
    console.log(`Submitting task for round ${round}`);
    await coreLogic.submitTask(round);
    
    console.log(`Auditing task for round ${round}`);
    await coreLogic.auditTask(round);
    
    await sleep(delay);
  }
  console.log("All tasks executed. Test completed.");
  process.exit(0);
}

executeTasks();
```

This implementation creates a simple task that adds two numbers (5 and 7) and stores the result. The submission function retrieves and submits this sum, while the audit function validates whether the submitted sum is correct.

The unit test file executes the task, submission, and audit functions for 10 rounds, with a delay between each round. This allows you to test both the submission and the audit processes.