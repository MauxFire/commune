
const { submission } = require('../task/submission');
const { audit } = require('../task/audit');
const { namespaceWrapper } = require('@_koii/namespace-wrapper');
const fs = require('fs');

jest.mock('@_koii/namespace-wrapper', () => ({
  namespaceWrapper: {
    storeSet: jest.fn(),
    storeGet: jest.fn(),
    submitTask: jest.fn(),
    validateAndVoteOnNodes: jest.fn(),
  },
}));

jest.mock('child_process', () => ({
  execSync: jest.fn(),
}));

jest.mock('fs', () => ({
  readFileSync: jest.fn(),
}));

describe('PyTorch to WASM Task', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('submission.task should run PyTorch model and convert to WASM', async () => {
    const mockWasmBuffer = Buffer.from('mock wasm data');
    fs.readFileSync.mockReturnValue(mockWasmBuffer);

    const result = await submission.task(1);
    expect(result).toBe('Model converted to WASM successfully');
    expect(namespaceWrapper.storeSet).toHaveBeenCalledWith('wasm_model', expect.any(String));
  });

  test('submission.submitTask should submit the stored WASM model', async () => {
    const mockWasmBase64 = 'bW9jayB3YXNtIGRhdGE=';
    namespaceWrapper.storeGet.mockResolvedValue(mockWasmBase64);

    await submission.submitTask(1);
    expect(namespaceWrapper.submitTask).toHaveBeenCalledWith(mockWasmBase64, 1);
  });

  test('audit.validateNode should correctly validate the WASM submission', async () => {
    const validSubmission = 'bW9jayB3YXNtIGRhdGE=';
    const invalidSubmission = 'not a base64 string';

    const isValid = await audit.validateNode(validSubmission, 1);
    expect(isValid).toBe(true);

    const isInvalid = await audit.validateNode(invalidSubmission, 1);
    expect(isInvalid).toBe(false);
  });

  test('audit.auditTask should call validateAndVoteOnNodes', async () => {
    await audit.auditTask(1);
    expect(namespaceWrapper.validateAndVoteOnNodes).toHaveBeenCalledWith(expect.any(Function), 1);
  });
});
