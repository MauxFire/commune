
const { namespaceWrapper } = require('@_koii/namespace-wrapper');
const tf = require('@tensorflow/tfjs');
require('@tensorflow/tfjs-node');

class Submission {
  constructor() {
    this.model = null;
  }

  async task(round) {
    try {
      console.log('Task called with round', round);
      
      // Create a simple neural network model
      this.model = tf.sequential({
        layers: [
          tf.layers.dense({ inputShape: [1], units: 1, useBias: true }),
          tf.layers.dense({ units: 1, useBias: true }),
        ]
      });
      
      // Compile the model
      this.model.compile({
        optimizer: tf.train.adam(),
        loss: tf.losses.meanSquaredError,
        metrics: ['mse'],
      });
      
      // Generate some random training data
      const xs = tf.randomNormal([100, 1]);
      const ys = xs.mul(2).add(1).add(tf.randomNormal([100, 1], 0, 0.1));
      
      // Train the model
      await this.model.fit(xs, ys, {
        epochs: 50,
        callbacks: {
          onEpochEnd: (epoch, logs) => console.log(`Epoch ${epoch}: loss = ${logs.loss}`)
        }
      });
      
      // Save the model weights
      const weightData = await this.model.getWeights()[0].data();
      await namespaceWrapper.storeSet('model_weights', JSON.stringify(Array.from(weightData)));
      
      return 'Model training completed';
    } catch (err) {
      console.error('ERROR IN EXECUTING TASK', err);
      return 'ERROR IN EXECUTING TASK: ' + err;
    }
  }

  async submitTask(roundNumber) {
    console.log('SubmitTask called with round', roundNumber);
    try {
      const weights = await namespaceWrapper.storeGet('model_weights');
      console.log('SUBMISSION', weights);
      await namespaceWrapper.submitTask(weights, roundNumber);
    } catch (error) {
      console.log('Error in submission', error);
    }
  }
}

const submission = new Submission();
module.exports = { submission };
