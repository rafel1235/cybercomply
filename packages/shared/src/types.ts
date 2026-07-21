// Tipi condivisi tra frontend (Next.js) e documentazione dei contratti API.
// Il backend FastAPI usa Pydantic per gli stessi contratti (apps/api/app/schemas);
// questo file è la fonte di verità lato client e va tenuto allineato manualmente
// finché non introduciamo generazione automatica da OpenAPI (prevista in Fase 3 avanzata).

export type OrganizationRole = "admin" | "viewer";

export interface User {
  id: string;
  email: string;
  fullName: string | null;
  createdAt: string;
}

export interface Organization {
  id: string;
  name: string;
  vatNumber: string | null;
  sector: string | null;
  employeeCount: number | null;
  annualRevenueEur: number | null;
  createdAt: string;
}

export interface OrganizationMember {
  userId: string;
  organizationId: string;
  role: OrganizationRole;
  invitedEmail?: string;
  joinedAt: string | null;
}

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
  user: User;
}

export interface ApiError {
  code: string;
  message: string;
}
