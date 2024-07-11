
const { namespaceWrapper } = require('@_koii/namespace-wrapper');

class Distribution {
  submitDistributionList = async round => {
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
  };

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
      let distributionCandidates = [];
      const taskAccountDataJSON = await namespaceWrapper.getTaskSubmissionInfo(round);
      
      if (taskAccountDataJSON == null) {
        console.error('ERROR IN FETCHING TASK SUBMISSION DATA');
        return distributionList;
      }

      const submissions = taskAccountDataJSON.submissions[round];
      const submissions_audit_trigger = taskAccountDataJSON.submissions_audit_trigger[round];

      if (submissions == null) {
        console.log(`NO SUBMISSIONS FOUND IN ROUND ${round}`);
        return distributionList;
      }

      const keys = Object.keys(submissions);
      const taskStakeListJSON = await namespaceWrapper.getTaskState({
        is_stake_list_required: true,
      });

      if (taskStakeListJSON == null) {
        console.error('ERROR IN FETCHING TASK STAKING LIST');
        return distributionList;
      }

      for (let candidatePublicKey of keys) {
        if (
          submissions_audit_trigger &&
          submissions_audit_trigger[candidatePublicKey]
        ) {
          const votes = submissions_audit_trigger[candidatePublicKey].votes;
          if (votes.length === 0) {
            const stake_list = taskStakeListJSON.stake_list;
            const candidateStake = stake_list[candidatePublicKey];
            const slashedStake = candidateStake * 0.7;
            distributionList[candidatePublicKey] = -slashedStake;
          } else {
            let numOfVotes = votes.reduce((acc, vote) => acc + (vote.is_valid ? 1 : -1), 0);
            if (numOfVotes < 0) {
              const stake_list = taskStakeListJSON.stake_list;
              const candidateStake = stake_list[candidatePublicKey];
              const slashedStake = candidateStake * 0.7;
              distributionList[candidatePublicKey] = -slashedStake;
            } else if (numOfVotes > 0) {
              distributionCandidates.push(candidatePublicKey);
            }
          }
        } else {
          distributionCandidates.push(candidatePublicKey);
        }
      }

      const reward = Math.floor(
        taskStakeListJSON.bounty_amount_per_round / distributionCandidates.length,
      );
      
      for (let candidate of distributionCandidates) {
        distributionList[candidate] = reward;
      }

      console.log('DISTRIBUTION LIST', distributionList);
      return distributionList;
    } catch (err) {
      console.log('ERROR IN GENERATING DISTRIBUTION LIST', err);
      return {};
    }
  }

  validateDistribution = async (
    distributionListSubmitter,
    round,
    _dummyDistributionList,
    _dummyTaskState,
  ) => {
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
      const generateDistributionList = await this.generateDistributionList(
        round,
        _dummyTaskState,
      );

      if (Object.keys(generateDistributionList).length === 0) {
        console.log('UNABLE TO GENERATE DISTRIBUTION LIST');
        return true;
      }
      const result = await this.shallowEqual(fetchedDistributionList, generateDistributionList);
      console.log('RESULT', result);
      return result;
    } catch (err) {
      console.log('ERROR IN VALIDATING DISTRIBUTION', err);
      return false;
    }
  };

  async shallowEqual(obj1, obj2) {
    const keys1 = Object.keys(obj1);
    const keys2 = Object.keys(obj2);
    if (keys1.length !== keys2.length) {
      return false;
    }
    for (let key of keys1) {
      if (obj1[key] !== obj2[key]) {
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