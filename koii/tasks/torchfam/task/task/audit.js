
const { namespaceWrapper } = require('@_koii/namespace-wrapper');
const tf = require('@tensorflow/tfjs');
require('@tensorflow/tfjs-node');

class Audit {
  async validateNode(submissionValue, round) {
    try {
      const weights = JSON.parse(submissionValue);
      
      // Recreate the model
      const model = tf.sequential({
        layers: [
          tf.layers.dense({ inputShape: [1], units: 1, useBias: true }),
          tf.layers.dense({ units: 1, useBias: true }),
        ]
      });
      
      // Set the weights
      model.layers[0].setWeights([tf.tensor2d(weights, [1, 1])]);
      
      // Test the model
      const testInput = tf.tensor2d([[1], [2], [3], [4]]);
      const predictions = model.predict(testInput);
      
      // Check if predictions are reasonable (close to y = 2x + 1)
      const expectedOutput = testInput.mul(2).add(1);
      const mse = tf.losses.meanSquaredError(expectedOutput, predictions).dataSync()[0];
      
      return mse < 0.1; // Consider it valid if MSE is less than 0.1
    } catch (e) {
      console.log('Error in validate:', e);
      return false;
    }
  }

  async auditTask(roundNumber) {
    console.log('AuditTask called with round', roundNumber);
    await namespaceWrapper.validateAndVoteOnNodes(this.validateNode, roundNumber);
  }
}

const audit = new Audit();
module.exports = { audit };
