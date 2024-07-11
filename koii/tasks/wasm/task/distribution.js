const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Distribution {
  async submitDistributionList(round) {
    console.log('SUBMIT DISTRIBUTION LIST CALLED WITH ROUND', round);
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
    console.log('AUDIT DISTRIBUTION CALLED WITHIN ROUND: ', roundNumber);
    await namespaceWrapper.validateAndVoteOnDistributionList(
      this.validateDistribution,
      roundNumber,
    );
  }

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
      
      const taskStakeListJSON = await namespaceWrapper.getTaskState({
        is_stake_list_required: true,
      });
      
      if (taskStakeListJSON == null) {
        console.error('ERROR IN FETCHING TASK STAKING LIST');
        return distributionList;
      }
      
      const bountyPerRound = taskStakeListJSON.bounty_amount_per_round;
      const stakeList = taskStakeListJSON.stake_list;
      
      // Distribute rewards equally among all valid submissions
      const validSubmissions = Object.entries(submissions).filter(([_, value]) => value !== null);
      const rewardPerSubmission = Math.floor(bountyPerRound / validSubmissions.length);
      
      for (const [publicKey, _] of validSubmissions) {
        distributionList[publicKey] = rewardPerSubmission;
      }
      
      console.log('DISTRIBUTION LIST', distributionList);
      return distributionList;
    } catch (err) {
      console.log('ERROR IN GENERATING DISTRIBUTION LIST', err);
      return {};
    }
  }

  async validateDistribution(
    distributionListSubmitter,
    round,
    _dummyDistributionList,
    _dummyTaskState,
  ) {
    try {
      console.log('DISTRIBUTION LIST SUBMITTER', distributionListSubmitter);
      const rawDistributionList = await namespaceWrapper.getDistributionList(
        distributionListSubmitter,
        round,
      );
      if (rawDistributionList == null) {
        return true;
      }
      const fetchedDistributionList = JSON.parse(rawDistributionList);
      console.log('FETCHED DISTRIBUTION LIST', fetchedDistributionList);
      
      const generatedDistributionList = await this.generateDistributionList(
        round,
        _dummyTaskState,
      );

      if (Object.keys(generatedDistributionList).length === 0) {
        console.log('UNABLE TO GENERATE DISTRIBUTION LIST');
        return true;
      }
      
      const result = this.compareDistributionLists(fetchedDistributionList, generatedDistributionList);
      console.log('DISTRIBUTION LIST COMPARISON RESULT', result);
      return result;
    } catch (err) {
      console.log('ERROR IN VALIDATING DISTRIBUTION', err);
      return false;
    }
  }

  compareDistributionLists(list1, list2) {
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
module.exports = {
  distribution,
};