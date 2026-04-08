import { Suspense } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { PageApp, PageFramework } from '@ansible/ansible-ui-framework';
import { ApmeMasthead } from './components/ApmeMasthead';
import { useApmeNavigation } from './hooks/useApmeNavigation';
import { useNotificationStream } from './hooks/useNotificationStream';

export function App() {
  return (
    <BrowserRouter>
      <PageFramework defaultRefreshInterval={30}>
        <Suspense fallback={<div style={{ padding: 48, textAlign: 'center' }}>Loading...</div>}>
          <ApmeApp />
        </Suspense>
      </PageFramework>
    </BrowserRouter>
  );
}

function ApmeApp() {
  const navigation = useApmeNavigation();
  useNotificationStream();
  return (
    <PageApp
      masthead={<ApmeMasthead />}
      navigation={navigation}
      defaultRefreshInterval={30}
    />
  );
}
