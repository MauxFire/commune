
const { submission } = require('../task/submission');
const { audit } = require('../task/audit');
const { namespaceWrapper } = require('@_koii/namespace-wrapper');
const tf = require('@tensorflow/tfjs');
require('@tensorflow/tfjs-node');

// Mock namespaceWrapper
jest.mock('@_koii/namespace-wrapper', () => ({
  namespaceWrapper: {
    storeSet: jest.fn(),
    storeGet: jest.fn(),
    submitTask: jest.fn(),
    validateAndVoteOnNodes: jest.fn(),
  },
}));

describe('Machine Learning Task', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('submission.task should train a model and store weights', async () => {
    const result = await submission.task(1);
    expect(result).toBe('Model training completed');
    expect(namespaceWrapper.storeSet).toHaveBeenCalledWith('model_weights', expect.any(String));
  });

  test('submission.submitTask should submit the stored weights', async () => {
    const mockWeights = JSON.stringify([1, 2, 3, 4]);
    namespaceWrapper.storeGet.mockResolvedValue(mockWeights);
    await submission.submitTask(1);
    expect(namespaceWrapper.submitTask).toHaveBeenCalledWith(mockWeights, 1);
  });

  test('audit.validateNode should correctly validate the model', async () => {
    const mockWeights = JSON.stringify([2, 1]); // Approximately y = 2x + 1
    const isValid = await audit.validateNode(mockWeights, 1);
    expect(isValid).toBe(true);

    const invalidWeights = JSON.stringify([10, 10]); // Very different from y = 2x + 1
    const isInvalid = await audit.validateNode(invalidWeights, 1);
    expect(isInvalid).toBe(false);
  });

  test('audit.auditTask should call validateAndVoteOnNodes', async () => {
    await audit.auditTask(1);
    expect(namespaceWrapper.validateAndVoteOnNodes).toHaveBeenCalledWith(expect.any(Function), 1);
  });
});
