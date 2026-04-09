/**
 * Hook that loads notifications from the Gateway REST API, connects to the
 * SSE stream for real-time updates, and pushes everything into the vendored
 * notification drawer (zustand) and alert toaster (context) stores.
 *
 * To avoid a gap between the initial REST load and SSE subscription, the
 * EventSource opens first and buffers incoming events.  After the REST
 * response arrives, buffered items are merged (id-based dedupe) so no
 * notification is lost.
 */

import { useEffect, useRef } from 'react';
import { usePageNotifications } from '@ansible/ansible-ui-framework';
import { usePageAlertToaster } from '@ansible/ansible-ui-framework/PageAlertToaster';
import type { IPageNotification } from '@ansible/ansible-ui-framework/PageNotifications/PageNotification';
import type { IPageNotificationGroup } from '@ansible/ansible-ui-framework/PageNotifications/PageNotificationGroup';
import { listNotifications, markNotificationRead } from '../services/api';
import type { NotificationItem } from '../types/api';

const GROUP_LABELS: Record<string, string> = {
  scan_complete: 'Scans',
  secrets_detected: 'Security',
  health_changed: 'Health',
};

function groupKey(n: NotificationItem): string {
  return GROUP_LABELS[n.type] ?? 'Other';
}

function toPageNotification(n: NotificationItem): IPageNotification {
  return {
    id: String(n.id),
    title: n.title,
    description: n.message,
    timestamp: n.created_at,
    variant: n.variant,
    to: n.link || undefined,
  };
}

function buildGroups(items: NotificationItem[]): Record<string, IPageNotificationGroup> {
  const groups: Record<string, IPageNotificationGroup> = {};
  for (const item of items) {
    const key = groupKey(item);
    if (!groups[key]) {
      groups[key] = { title: key, notifications: [] };
    }
    groups[key].notifications.push(toPageNotification(item));
  }
  return groups;
}

function mergeNotification(
  existing: Record<string, IPageNotificationGroup>,
  item: NotificationItem,
): Record<string, IPageNotificationGroup> {
  const key = groupKey(item);
  const next = { ...existing };
  const group = next[key]
    ? { ...next[key], notifications: [...next[key].notifications] }
    : { title: key, notifications: [] };

  const strId = String(item.id);
  if (!group.notifications.some((n) => n.id === strId)) {
    group.notifications.unshift(toPageNotification(item));
  }
  next[key] = group;
  return next;
}

const NO_DISMISS_TYPES = new Set(['secrets_detected']);

export function useNotificationStream(): void {
  const { setNotificationGroups } = usePageNotifications();
  const alertToaster = usePageAlertToaster();
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    let es: EventSource | undefined;

    const startStream = async () => {
      // Buffer SSE events that arrive before the REST load completes.
      const buffer: NotificationItem[] = [];
      let restLoaded = false;

      const proto = window.location.protocol === 'https:' ? 'https:' : 'http:';
      const sseUrl = `${proto}//${window.location.host}/api/v1/notifications/stream`;
      es = new EventSource(sseUrl);

      const handleSseItem = (item: NotificationItem) => {
        setNotificationGroups((prev) => mergeNotification(prev, item));

        const timeout = NO_DISMISS_TYPES.has(item.type) ? undefined : 8000;
        alertToaster.addAlert({
          key: `notif-${item.id}`,
          title: item.title,
          children: item.message,
          variant: item.variant,
          timeout,
          actionClose: undefined,
        });

        markNotificationRead(item.id).catch(() => {});
      };

      es.onmessage = (event) => {
        if (!mountedRef.current) return;
        let item: NotificationItem;
        try {
          item = JSON.parse(event.data as string) as NotificationItem;
        } catch {
          return;
        }

        if (!restLoaded) {
          buffer.push(item);
          return;
        }

        handleSseItem(item);
      };

      es.onerror = () => {
        // EventSource auto-reconnects — nothing to do
      };

      try {
        const resp = await listNotifications(100, 0);
        if (!mountedRef.current) return;

        // Switch to live mode before draining the buffer so any events
        // arriving from this point forward go through handleSseItem
        // instead of accumulating in the buffer.
        restLoaded = true;

        const restIds = new Set(resp.items.map((n) => n.id));
        const merged = [...resp.items];
        const pending = buffer.splice(0);
        for (const buffered of pending) {
          if (!restIds.has(buffered.id)) {
            merged.unshift(buffered);
          }
        }

        setNotificationGroups(() => buildGroups(merged));

        for (const buffered of pending) {
          if (!restIds.has(buffered.id)) {
            const timeout = NO_DISMISS_TYPES.has(buffered.type) ? undefined : 8000;
            alertToaster.addAlert({
              key: `notif-${buffered.id}`,
              title: buffered.title,
              children: buffered.message,
              variant: buffered.variant,
              timeout,
              actionClose: undefined,
            });
            markNotificationRead(buffered.id).catch(() => {});
          }
        }
      } catch {
        // Gateway may be unavailable — silent degradation
        restLoaded = true;
        if (!mountedRef.current) return;
      }
    };

    void startStream();

    return () => {
      mountedRef.current = false;
      es?.close();
    };
  }, [setNotificationGroups, alertToaster]);
}
