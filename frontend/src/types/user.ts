export interface UserProfile {
  name: string;
  email: string;
  plan: string;
  tradingStyle: string;
}

export interface AppNotification {
  id: string;
  title: string;
  detail: string;
  at: string;
  unread: boolean;
}
