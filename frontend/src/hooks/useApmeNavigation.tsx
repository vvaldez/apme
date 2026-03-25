import { useMemo } from 'react';
import type { PageNavigationItem } from '@ansible/ansible-ui-framework';
import { DashboardPage } from '../pages/DashboardPage';
import { ProjectsPage } from '../pages/ProjectsPage';
import { ProjectDetailPage } from '../pages/ProjectDetailPage';
import { PlaygroundPage } from '../pages/PlaygroundPage';
import { ActivityPage } from '../pages/ActivityPage';
import { ActivityDetailPage } from '../pages/ActivityDetailPage';
import { HealthPage } from '../pages/HealthPage';
import { SettingsPage } from '../pages/SettingsPage';

export function useApmeNavigation(): PageNavigationItem[] {
  return useMemo<PageNavigationItem[]>(
    () => [
      {
        label: 'Overview',
        path: '',
        children: [
          { id: 'dashboard', path: '', label: 'Dashboard', element: <DashboardPage /> },
        ],
      },
      {
        label: 'Projects',
        path: '',
        children: [
          { id: 'projects', path: 'projects', label: 'Projects', element: <ProjectsPage /> },
          { id: 'project-detail', path: 'projects/:projectId', element: <ProjectDetailPage />, hidden: true },
        ],
      },
      {
        label: 'Operations',
        path: '',
        children: [
          { id: 'playground', path: 'playground', label: 'Playground', element: <PlaygroundPage /> },
          { id: 'activity', path: 'activity', label: 'Activity', element: <ActivityPage /> },
          { id: 'activity-detail', path: 'activity/:activityId', element: <ActivityDetailPage />, hidden: true },
        ],
      },
      {
        label: 'System',
        path: '',
        children: [
          { id: 'health', path: 'health', label: 'Health', element: <HealthPage /> },
          { id: 'settings', path: 'settings', label: 'Settings', element: <SettingsPage /> },
        ],
      },
    ],
    [],
  );
}
