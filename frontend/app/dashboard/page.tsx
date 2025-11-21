'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Heart, TrendingUp, DollarSign, Bell, LogOut, Plus, Target } from 'lucide-react';
import { TokenManager } from '@/lib/api';

interface Campaign {
  id: string;
  title: string;
  description: string;
  goal_amount: number;
  current_amount: number;
  deadline: string;
  status: string;
  created_at: string;
}

interface Payment {
  id: string;
  amount: number;
  campaign_id: string;
  status: string;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [myCampaigns, setMyCampaigns] = useState<Campaign[]>([]);
  const [myDonations, setMyDonations] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const token = TokenManager.getToken();
    const userData = TokenManager.getUser();

    if (!token || !userData) {
      router.push('/login');
      return;
    }

    setUser(userData);
    fetchDashboardData(token);
  }, [router]);

  const fetchDashboardData = async (token: string) => {
    try {
      // Fetch user's campaigns
      const campaignsRes = await fetch('http://localhost:8000/api/v1/campaigns/my', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (campaignsRes.ok) {
        setMyCampaigns(await campaignsRes.json());
      }

      // Fetch user's donations
      const paymentsRes = await fetch('http://localhost:8000/api/v1/payments/my', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (paymentsRes.ok) {
        setMyDonations(await paymentsRes.json());
      }

      // Fetch unread notifications count
      const notifRes = await fetch('http://localhost:8000/api/v1/notifications/unread', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (notifRes.ok) {
        const data = await notifRes.json();
        setUnreadCount(data.unread_count || 0);
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    TokenManager.removeToken();
    TokenManager.removeUser();
    router.push('/login');
  };

  const calculateProgress = (current: number, goal: number) => {
    return Math.min((current / goal) * 100, 100);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const totalRaised = myCampaigns.reduce((sum, c) => sum + c.current_amount, 0);
  const totalDonated = myDonations.reduce((sum, p) => sum + p.amount, 0);

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white dark:from-zinc-950 dark:to-zinc-900">
      {/* Header */}
      <header className="border-b bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2">
            <Heart className="h-6 w-6 text-blue-600 fill-blue-600" />
            <span className="text-xl font-bold">CareForAll</span>
          </Link>
          <nav className="flex items-center gap-4">
            <Link href="/campaigns">
              <Button variant="ghost">Campaigns</Button>
            </Link>
            <Link href="/notifications" className="relative">
              <Button variant="ghost">
                <Bell className="h-4 w-4" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-red-600 text-xs text-white flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </Button>
            </Link>
            <Button onClick={handleLogout} variant="outline">
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </Button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Welcome back, {user.email}</h1>
          <p className="text-zinc-600 dark:text-zinc-400">
            Here's an overview of your campaigns and contributions
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
          <Card>
            <CardHeader className="pb-3">
              <CardDescription className="flex items-center gap-2">
                <Target className="h-4 w-4" />
                My Campaigns
              </CardDescription>
              <CardTitle className="text-3xl">{myCampaigns.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Total Raised
              </CardDescription>
              <CardTitle className="text-3xl text-green-600">{formatCurrency(totalRaised)}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription className="flex items-center gap-2">
                <Heart className="h-4 w-4" />
                Total Donated
              </CardDescription>
              <CardTitle className="text-3xl text-blue-600">{formatCurrency(totalDonated)}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription className="flex items-center gap-2">
                <Bell className="h-4 w-4" />
                Notifications
              </CardDescription>
              <CardTitle className="text-3xl text-orange-600">{unreadCount}</CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Tabs for Campaigns and Donations */}
        <Tabs defaultValue="campaigns" className="space-y-6">
          <TabsList>
            <TabsTrigger value="campaigns">My Campaigns</TabsTrigger>
            <TabsTrigger value="donations">My Donations</TabsTrigger>
          </TabsList>

          <TabsContent value="campaigns" className="space-y-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold">Your Campaigns</h2>
              <Link href="/campaigns/create">
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Campaign
                </Button>
              </Link>
            </div>

            {loading ? (
              <p className="text-center py-8 text-zinc-600">Loading campaigns...</p>
            ) : myCampaigns.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Target className="h-12 w-12 text-zinc-400 mx-auto mb-4" />
                  <p className="text-zinc-600 mb-4">You haven't created any campaigns yet</p>
                  <Link href="/campaigns/create">
                    <Button>Start Your First Campaign</Button>
                  </Link>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {myCampaigns.map((campaign) => {
                  const progress = calculateProgress(campaign.current_amount, campaign.goal_amount);
                  return (
                    <Card key={campaign.id} className="hover:shadow-lg transition-shadow">
                      <CardHeader>
                        <div className="flex items-center justify-between mb-2">
                          <Badge variant={campaign.status === 'active' ? 'default' : 'secondary'}>
                            {campaign.status}
                          </Badge>
                        </div>
                        <CardTitle className="line-clamp-1">{campaign.title}</CardTitle>
                        <CardDescription className="line-clamp-2">
                          {campaign.description}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div>
                          <div className="flex justify-between text-sm mb-2">
                            <span className="font-semibold text-blue-600">
                              {formatCurrency(campaign.current_amount)}
                            </span>
                            <span className="text-zinc-600">
                              of {formatCurrency(campaign.goal_amount)}
                            </span>
                          </div>
                          <Progress value={progress} className="h-2" />
                          <p className="text-xs text-zinc-500 mt-1">{progress.toFixed(0)}% funded</p>
                        </div>
                        <Link href={`/campaigns/${campaign.id}`}>
                          <Button variant="outline" className="w-full">
                            View Details
                          </Button>
                        </Link>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

          <TabsContent value="donations" className="space-y-4">
            <h2 className="text-2xl font-bold mb-4">Your Donations</h2>

            {loading ? (
              <p className="text-center py-8 text-zinc-600">Loading donations...</p>
            ) : myDonations.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Heart className="h-12 w-12 text-zinc-400 mx-auto mb-4" />
                  <p className="text-zinc-600 mb-4">You haven't made any donations yet</p>
                  <Link href="/campaigns">
                    <Button>Browse Campaigns</Button>
                  </Link>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="pt-6">
                  <div className="space-y-3">
                    {myDonations.map((payment) => (
                      <div
                        key={payment.id}
                        className="flex items-center justify-between p-4 rounded-lg bg-zinc-50 dark:bg-zinc-800"
                      >
                        <div>
                          <p className="font-medium text-green-600">
                            {formatCurrency(payment.amount)}
                          </p>
                          <p className="text-sm text-zinc-600">
                            {new Date(payment.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <Badge variant="outline">{payment.status}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
