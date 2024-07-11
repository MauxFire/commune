
// The distribution.js file remains largely unchanged for this simple task
// You can keep the existing distribution.js file as it is

const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Distribution {
  // ... (keep the existing methods)

  async generateDistributionList(round, _dummyTaskState) {
    try {
      console.log('GENERATE DISTRIBUTION LIST CALLED WITH ROUND', round);
      let distributionList = {};
      let taskAccountDataJSON = await namespaceWrapper.getTaskSubmissionInfo(round);
      
      if (taskAccountDataJSON == null) {
        console.error('ERROR IN FETCHING TASK SUBMISSION DATA');
        return distributionList;
      }

      const submissions = taskAccountDataJSON.submissions[round];
      if (submissions == null) {
        console.log(`NO SUBMISSIONS FOUND IN ROUND ${round}`);
        return distributionList;
      }

      const keys = Object.keys(submissions);
      const reward = Math.floor(100000000 / keys.length); // Assuming a total reward of 1 KOII (100000000 lamports)

      for (let i = 0; i < keys.length; i++) {
        distributionList[keys[i]] = reward;
      }

      console.log('DISTRIBUTION LIST', distributionList);
      return distributionList;
    } catch (err) {
      console.log('ERROR IN GENERATING DISTRIBUTION LIST', err);
      return {};
    }
  }

  // ... (keep the other existing methods)
}

const distribution = new Distribution();
module.exports = { distribution };