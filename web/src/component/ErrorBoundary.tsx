import { intl } from '@/utils/intl';
import { history } from 'umi';
import React from 'react';
import { Alert, Button } from '@oceanbase/design';
import Empty from '@/component/Empty';

interface ErrorBoundaryProps {
  message?: React.ReactNode;
  description?: React.ReactNode;
}

interface ErrorBoundaryState {
  error?: Error | null;
  info: {
    componentStack?: string;
  };
}

class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state = {
    error: undefined,
    info: {
      componentStack: '',
    },
  };

  componentDidCatch(error: Error | null, info: object) {
    this.setState({ error, info });
  }

  render() {
    const { message, description, children } = this.props;
    const { error, info } = this.state;
    const componentStack =
      info && info.componentStack ? info.componentStack : null;
    const errorMessage =
      typeof message === 'undefined' ? (error || '').toString() : message;
    const errorDescription =
      typeof description === 'undefined' ? componentStack : description;
    if (error) {
      return (
        <Empty
          mode="page"
          image="/assets/common/crash.svg"
          title={intl.formatMessage({
            id: 'OBD.src.component.ErrorBoundary.PageExecutionError',
            defaultMessage: '页面执行出错',
          })}
        >
          <Button
            type="primary"
            onClick={() => {
              history.push('/');
              // 刷新页面，以便重新加载应用、避免停留在当前的 ErrorBoundary 页面
              window.location.reload();
            }}
          >
            {intl.formatMessage({
              id: 'OBD.src.component.ErrorBoundary.ReturnToHomePage',
              defaultMessage: '返回首页',
            })}
          </Button>
          {/* 展示报错详情，方便定位问题原因 */}
          <Alert
            type="error"
            showIcon={true}
            message={errorMessage}
            description={errorDescription}
            style={{
              marginTop: 24,
              overflow: 'auto',
              maxHeight: '50vh',
              // 为了避免被 Empty 的水平居中样式影响，需要设置 textAlign
              textAlign: 'left',
            }}
          />
        </Empty>
      );
    }
    return children;
  }
}

export default ErrorBoundary;
