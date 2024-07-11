
```javascript
const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Distribution {
  async submitDistributionList(round) {
    console.log('Submit distribution list called with round', round);
    try {
      const distributionList = await this.generateDistributionList(round);
      if (Object.keys(distributionList).length === 0) {
        console.log('NO DISTRIBUTION LIST GENERATED');
        return;
      }
      const decider = await namespaceWrapper.uploadDistributionList(
        distributionList,
        round,
      );
      console.log('DECIDER', decider);
      if (decider) {
        const response =
          await namespaceWrapper.distributionListSubmissionOnChain(round);
        console.log('RESPONSE FROM DISTRIBUTION LIST', response);
      }
    } catch (err) {
      console.log('ERROR IN SUBMIT DISTRIBUTION', err);
    }
  }

  async auditDistribution(roundNumber) {
    console.log('Audit distribution called within round:', roundNumber);
    await namespaceWrapper.validateAndVoteOnDistributionList(
      this.validateDistribution,
      roundNumber,
    );
  }

  async generateDistributionList(round) {
    try {
      console.log('Generate distribution list called with round', round);
      let distributionList = {};
      const taskAccountDataJSON = await namespaceWrapper.getTaskSubmissionInfo(round);
      
      if (taskAccountDataJSON == null) {
        console.error('ERROR IN FETCHING TASK SUBMISSION DATA');
        return distributionList;
      }

      const submissions = taskAccountDataJSON.submissions[round];
      if (submissions == null) {
        console.log(`NO SUBMISSIONS FOUND IN ROUND ${round}`);
        return distributionList;
      }

      const validSubmitters = Object.keys(submissions);
      const reward = Math.floor(100 / validSubmitters.length); // Assuming 100 KOII tokens per round

      for (let submitter of validSubmitters) {
        distributionList[submitter] = reward;
      }

      console.log('DISTRIBUTION LIST', distributionList);
      return distributionList;
    } catch (err) {
      console.log('ERROR IN GENERATING DISTRIBUTION LIST', err);
      return {};
    }
  }

  async validateDistribution(distributionListSubmitter, round, _dummyDistributionList) {
    try {
      console.log('DISTRIBUTION LIST SUBMITTER', distributionListSubmitter);
      const rawDistributionList = await namespaceWrapper.getDistributionList(
        distributionListSubmitter,
        round,
      );
      let fetchedDistributionList = rawDistributionList ? JSON.parse(rawDistributionList) : null;
      console.log('FETCHED DISTRIBUTION LIST', fetchedDistributionList);

      const generatedDistributionList = await this.generateDistributionList(round);

      if (Object.keys(generatedDistributionList).length === 0) {
        console.log('UNABLE TO GENERATE DISTRIBUTION LIST');
        return true;
      }

      const result = this.compareDistributionLists(fetchedDistributionList, generatedDistributionList);
      console.log('VALIDATION RESULT', result);
      return result;
    } catch (err) {
      console.log('ERROR IN VALIDATING DISTRIBUTION', err);
      return false;
    }
  }

  compareDistributionLists(list1, list2) {
    if (typeof list1 === 'string') {
      list1 = JSON.parse(list1);
    }
    if (typeof list2 === 'string') {
      list2 = JSON.parse(list2);
    }

    const keys1 = Object.keys(list1);
    const keys2 = Object.keys(list2);

    if (keys1.length !== keys2.length) {
      return false;
    }

    for (let key of keys1) {
      if (list1[key] !== list2[key]) {
        return false;
      }
    }
    return true;
  }
}

const distribution = new Distribution();
module.exports = { distribution };
```

These files create a task that multiplies random numbers, submits the result, audits the submissions, and distributes rewards. The submission.js file handles the main task logic, audit.js validates the submissions, and distribution.js manages the reward distribution.