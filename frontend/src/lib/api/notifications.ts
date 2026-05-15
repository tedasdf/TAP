import { apiRequest } from "@/lib/api/client";
import type { ApiNotification } from "@/lib/types/api";

export function getNotifications() {
  return apiRequest<ApiNotification[]>("/notifications");
}

export function getUnreadNotifications() {
  return apiRequest<ApiNotification[]>("/notifications?unread_only=true");
}

export function markNotificationRead(notificationId: string) {
  return apiRequest<ApiNotification>(`/notifications/${notificationId}/read`, {
    method: "POST",
  });
}

export function markAllNotificationsRead() {
  return apiRequest<{ updated_count: number }>("/notifications/read-all", {
    method: "POST",
  });
}