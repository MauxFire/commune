const { submission } = require('../task/submission');
const { audit } = require('../task/audit');
const { namespaceWrapper } = require('@_koii/namespace-wrapper');

// Mock namespaceWrapper
jest.mock('@_koii/namespace-wrapper', () => ({
  namespaceWrapper: {
    storeSet: jest.fn(),
    storeGet: jest.fn(),
    submitTask: jest.fn(),
    validateAndVoteOnNodes: jest.fn(),
  },
}));

describe('Adder Task', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('submission.task should store two random numbers and their sum', async () => {
    const result = await submission.task(1);
    expect(result).toBe('Addition completed');
    expect(namespaceWrapper.storeSet).toHaveBeenCalledTimes(3);
  });

  test('submission.submitTask should submit the stored result', async () => {
    namespaceWrapper.storeGet.mockResolvedValue('42');
    await submission.submitTask(1);
    expect(namespaceWrapper.submitTask).toHaveBeenCalledWith('42', 1);
  });

  test('audit.validateNode should correctly validate the sum', async () => {
    namespaceWrapper.storeGet.mockImplementation((key) => {
      if (key === 'num1') return '20';
      if (key === 'num2') return '22';
      return '42';
    });

    const isValid = await audit.validateNode('42', 1);
    expect(isValid).toBe(true);

    const isInvalid = await audit.validateNode('43', 1);
    expect(isInvalid).toBe(false);
  });

  test('audit.auditTask should call validateAndVoteOnNodes', async () => {
    await audit.auditTask(1);
    expect(namespaceWrapper.validateAndVoteOnNodes).toHaveBeenCalledWith(expect.any(Function), 1);
  });
});