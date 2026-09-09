import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import api from "../api/api";
import { useAuth } from "../context/AuthContext";
import { 
  Users, Shield, BarChart3, Plus, Check, X, Loader2, 
  Search, Trash2, CheckCircle2, AlertCircle 
} from "lucide-react";
import anigenLogo from "../assets/AnigenLogo.png";

interface User {
  id: number;
  username: string;
  email: string;
  is_admin: boolean;
  is_beta_authorized: boolean;
  created_at: string;
}

interface AdminStats {
  total_users?: number;
  beta_users?: number;
  total_jobs?: number;
  completed_jobs?: number;
}

const AdminPanel: React.FC = () => {
  const { logout } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newUser, setNewUser] = useState({ username: "", password: "", email: "" });
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "pending" | "approved" | "admins">("all");
  const [deleteConfirmUser, setDeleteConfirmUser] = useState<User | null>(null);

  const fetchData = async () => {
    try {
      const [uRes, sRes] = await Promise.all([
        api.get("/admin/users"),
        api.get("/admin/stats"),
      ]);
      setUsers(uRes.data);
      setStats(sRes.data);
    } catch (err) {
      console.error("Failed to fetch admin data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/admin/users/create", newUser);
      setShowCreateModal(false);
      setNewUser({ username: "", password: "", email: "" });
      await fetchData();
    } catch (err: unknown) {
      let msg = "Failed to create user";
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (Array.isArray(detail)) {
          msg = detail.map((d: { loc: (string | number)[]; msg: string }) => `${d.loc[d.loc.length - 1]}: ${d.msg}`).join("\n");
        } else if (typeof detail === "string") {
          msg = detail;
        } else {
          msg = err.message;
        }
      } else if (err instanceof Error) {
        msg = err.message;
      }
      alert(msg);
    }
  };

  const handleToggleAuth = async (userId: number, currentAuth: boolean) => {
    setActionLoading(userId);
    try {
      await api.put(`/admin/users/${userId}/approve`, { authorized: !currentAuth });
      await fetchData();
    } catch {
      alert("Action failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteUser = async () => {
    if (!deleteConfirmUser) return;
    setActionLoading(deleteConfirmUser.id);
    try {
      await api.delete(`/admin/users/${deleteConfirmUser.id}`);
      setDeleteConfirmUser(null);
      await fetchData();
    } catch {
      alert("Delete failed");
    } finally {
      setActionLoading(null);
    }
  };

  // Filtered users
  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (statusFilter === "pending") return !u.is_beta_authorized && !u.is_admin;
    if (statusFilter === "approved") return u.is_beta_authorized;
    if (statusFilter === "admins") return u.is_admin;
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center text-zinc-900">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-orange-600 animate-spin" />
          <span className="text-xs font-mono text-zinc-500">Loading Studio Admin Console...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A] p-6 md:p-10 font-sans selection:bg-orange-100 selection:text-orange-900">
      {/* Delete Confirmation Modal */}
      {deleteConfirmUser && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white border border-red-200 rounded-2xl p-6 sm:p-8 max-w-sm w-full shadow-2xl text-center space-y-4">
            <div className="w-14 h-14 bg-red-50 text-red-600 border border-red-200 rounded-2xl flex items-center justify-center mx-auto">
              <Trash2 size={24} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-zinc-900">Revoke & Delete User</h2>
              <p className="text-zinc-600 text-xs mt-1 leading-relaxed">
                Permanently delete <span className="text-zinc-900 font-bold">{deleteConfirmUser.username}</span>? All associated job records and beta tokens will be purged.
              </p>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setDeleteConfirmUser(null)}
                className="flex-1 py-2 bg-zinc-100 text-zinc-700 rounded-xl hover:bg-zinc-200 transition-colors text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteUser}
                className="flex-1 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl transition-colors text-xs shadow-xs"
              >
                Confirm Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white border border-zinc-200 rounded-2xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <h2 className="text-lg font-bold text-zinc-900">Direct User Provisioning</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-zinc-400 hover:text-zinc-700"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700">Username</label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-white border border-zinc-200 rounded-xl text-xs text-zinc-900 focus:border-orange-500 outline-none"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700">Email Address</label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-white border border-zinc-200 rounded-xl text-xs text-zinc-900 focus:border-orange-500 outline-none"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700">Initial Password</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-white border border-zinc-200 rounded-xl text-xs text-zinc-900 focus:border-orange-500 outline-none"
                  required
                />
              </div>

              <div className="flex gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 py-2.5 bg-zinc-100 text-zinc-700 rounded-xl hover:bg-zinc-200 transition-colors text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-zinc-900 hover:bg-zinc-800 text-white font-semibold rounded-xl transition-colors text-xs shadow-xs"
                >
                  Create Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Main Admin Console Container */}
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header Bar */}
        <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-200 pb-6">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-700 shadow-xs">
              <Shield size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-extrabold text-zinc-900 tracking-tight">Studio Admin Console</h1>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200 font-bold">
                  Supervisor Mode
                </span>
              </div>
              <p className="text-xs text-zinc-500 mt-0.5">Control Remotion video queue access and authorization grants.</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/dashboard"
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50 text-xs font-semibold transition-all shadow-xs"
            >
              <img src={anigenLogo} alt="AniGenerator" className="w-4 h-4 object-contain rounded" />
              <span>Studio Workspace</span>
            </Link>
            <button
              onClick={logout}
              className="px-3.5 py-2 rounded-xl border border-zinc-200 bg-white text-zinc-600 hover:text-zinc-900 text-xs font-semibold transition-colors shadow-xs"
            >
              Sign Out
            </button>
          </div>
        </header>

        {/* Stats Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div className="p-5 rounded-2xl border border-zinc-200 bg-white shadow-xs">
            <div className="flex items-center justify-between text-zinc-500 mb-2">
              <span className="text-xs font-mono uppercase tracking-wider">Total Registered</span>
              <Users size={18} className="text-orange-600" />
            </div>
            <div className="text-3xl font-extrabold text-zinc-900 font-mono">{stats?.total_users || 0}</div>
            <p className="text-[10px] text-zinc-500 font-mono mt-1">Platform Accounts</p>
          </div>

          <div className="p-5 rounded-2xl border border-zinc-200 bg-white shadow-xs">
            <div className="flex items-center justify-between text-zinc-500 mb-2">
              <span className="text-xs font-mono uppercase tracking-wider">Beta Authorized</span>
              <CheckCircle2 size={18} className="text-emerald-600" />
            </div>
            <div className="text-3xl font-extrabold text-zinc-900 font-mono">{stats?.beta_users || 0}</div>
            <p className="text-[10px] text-zinc-500 font-mono mt-1">Active Rendering Rights</p>
          </div>

          <div className="p-5 rounded-2xl border border-zinc-200 bg-white shadow-xs">
            <div className="flex items-center justify-between text-zinc-500 mb-2">
              <span className="text-xs font-mono uppercase tracking-wider">24h Remotion Jobs</span>
              <BarChart3 size={18} className="text-sky-600" />
            </div>
            <div className="text-3xl font-extrabold text-zinc-900 font-mono">
              {stats?.completed_jobs || 0} <span className="text-base text-zinc-400 font-normal">/ {stats?.total_jobs || 0}</span>
            </div>
            <p className="text-[10px] text-zinc-500 font-mono mt-1">Render Success Rate</p>
          </div>
        </div>

        {/* Access Requests Table Card */}
        <div className="rounded-2xl border border-zinc-200 bg-white overflow-hidden shadow-xs">
          {/* Action Bar: Search, Filters, Create */}
          <div className="p-5 border-b border-zinc-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
            {/* Search Input */}
            <div className="relative flex-1 max-w-sm">
              <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by username or email..."
                className="w-full pl-9 pr-4 py-2 bg-white border border-zinc-200 rounded-xl text-xs text-zinc-900 placeholder-zinc-400 focus:border-orange-500 outline-none"
              />
            </div>

            {/* Filter Tabs & Create */}
            <div className="flex items-center gap-3">
              <div className="flex items-center p-1 bg-zinc-100 rounded-xl border border-zinc-200 text-xs font-mono">
                {[
                  { id: "all", label: "All" },
                  { id: "pending", label: "Pending" },
                  { id: "approved", label: "Approved" },
                  { id: "admins", label: "Admins" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setStatusFilter(tab.id as "all" | "pending" | "approved" | "admins")}
                    className={`px-3 py-1 rounded-lg transition-all ${
                      statusFilter === tab.id
                        ? "bg-white text-zinc-900 font-bold shadow-xs"
                        : "text-zinc-600 hover:text-zinc-900"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-orange-600 hover:bg-orange-700 text-white text-xs font-semibold shadow-xs transition-all"
              >
                <Plus size={15} />
                <span>New User</span>
              </button>
            </div>
          </div>

          {/* User Rows Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-zinc-500 border-b border-zinc-200 bg-zinc-50 font-mono uppercase text-[10px]">
                  <th className="px-6 py-3.5">User Identity</th>
                  <th className="px-6 py-3.5">Permissions</th>
                  <th className="px-6 py-3.5">Beta Access</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-10 text-center text-zinc-400 font-mono">
                      No matching user accounts located.
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((u) => {
                    const isLoading = actionLoading === u.id;

                    return (
                      <tr key={u.id} className="hover:bg-zinc-50/60 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-zinc-100 border border-zinc-200 flex items-center justify-center font-bold text-zinc-700 uppercase text-xs">
                              {u.username.slice(0, 2)}
                            </div>
                            <div>
                              <p className="font-bold text-zinc-900">{u.username}</p>
                              <p className="text-[11px] text-zinc-500 font-mono">{u.email}</p>
                            </div>
                          </div>
                        </td>

                        <td className="px-6 py-4 font-mono">
                          {u.is_admin ? (
                            <span className="px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200 text-[10px] font-bold">
                              SUPER_ADMIN
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-600 border border-zinc-200 text-[10px]">
                              CREATOR
                            </span>
                          )}
                        </td>

                        <td className="px-6 py-4">
                          <button
                            onClick={() => handleToggleAuth(u.id, u.is_beta_authorized)}
                            disabled={isLoading || u.is_admin}
                            className={`px-3 py-1 rounded-lg text-[11px] font-mono font-bold flex items-center gap-1.5 transition-all ${
                              u.is_beta_authorized
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
                                : "bg-orange-50 text-orange-800 border border-orange-200 hover:bg-orange-100"
                            } ${u.is_admin ? "opacity-60 cursor-not-allowed" : ""}`}
                          >
                            {isLoading ? (
                              <Loader2 size={12} className="animate-spin" />
                            ) : u.is_beta_authorized ? (
                              <>
                                <Check size={12} />
                                <span>Authorized</span>
                              </>
                            ) : (
                              <>
                                <AlertCircle size={12} />
                                <span>Pending Approval</span>
                              </>
                            )}
                          </button>
                        </td>

                        <td className="px-6 py-4 text-right">
                          {!u.is_admin && (
                            <button
                              onClick={() => setDeleteConfirmUser(u)}
                              className="p-1.5 rounded-lg text-zinc-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                              title="Delete Account"
                            >
                              <Trash2 size={15} />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;
