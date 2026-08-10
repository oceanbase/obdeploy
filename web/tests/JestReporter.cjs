class JestReporter {
  onTestResult(_test, result) {
    if (result.failureMessage) {
      console.error(result.failureMessage);
    }
    result.testResults.forEach((testResult) => {
      if (testResult.status === 'failed') {
        console.error(`FAIL ${testResult.fullName}`);
        testResult.failureMessages.forEach((message) => console.error(message));
      }
    });
  }

  onRunComplete(_contexts, results) {
    const failedSuites = results.numFailedTestSuites;
    const runtimeErrorSuites = results.numRuntimeErrorTestSuites;
    const status = results.numFailedTests === 0 &&
      failedSuites === 0 && runtimeErrorSuites === 0
      ? 'PASS'
      : 'FAIL';
    console.log(
      `${status}: ${results.numPassedTests} passed, ` +
      `${results.numFailedTests} failed, ${results.numTotalTests} total; ` +
      `${failedSuites} failed suites, ${runtimeErrorSuites} runtime-error suites`,
    );
  }
}

module.exports = JestReporter;
