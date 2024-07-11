
const { submission } = require('../task/submission');
const { audit } = require('../task/audit');

// Mock WebAssembly and namespaceWrapper
global.WebAssembly = {
  instantiateStreaming: async () => ({
    instance: {
      exports: {
        add: (a, b) => a + b
      }
    }
  })
};

global.fetch = () => Promise.resolve();

const mockNamespaceWrapper = {
  storeSet: jest.fn(),
  storeGet: jest.fn(),
  getSlot: jest.fn(),
  checkSubmissionAndUpdateRound: jest.fn(),
  validateAndVoteOnNodes: jest.fn(),
};

jest.mock('@_koii/namespace-wrapper', () => ({
  namespaceWrapper: mockNamespaceWrapper,
}));

describe('WASM Task Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('Submission task should execute WASM and store result', async () => {
    const result = await submission.task(1);
    expect(result).toBe('WASM result: 8');
    expect(mockNamespaceWrapper.storeSet).toHaveBeenCalledWith('value', 'WASM result: 8');
  });

  test('Submission submitTask should fetch and submit the stored value', async () => {
    mockNamespaceWrapper.storeGet.mockResolvedValue('WASM result: 8');
    const result = await submission.submitTask(1);
    expect(result).toBe('WASM result: 8');
    expect(mockNamespaceWrapper.checkSubmissionAndUpdateRound).toHaveBeenCalled();
  });

  test('Audit validateNode should correctly validate the WASM result', async () => {
    const validResult = await audit.validateNode('WASM result: 8', 1);
    expect(validResult).toBe(true);

    const invalidResult = await audit.validateNode('WASM result: 10', 1);
    expect(invalidResult).toBe(false);
  });

  test('Audit auditTask should call validateAndVoteOnNodes', async () => {
    await audit.auditTask(1);
    expect(mockNamespaceWrapper.validateAndVoteOnNodes).toHaveBeenCalled();
  });
});
