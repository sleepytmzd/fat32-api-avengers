'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Heart, Calendar, Target, TrendingUp, ArrowLeft, DollarSign, Users } from 'lucide-react';
import { TokenManager } from '@/lib/api';

interface Campaign {
  id: string;
  title: string;
  description: string;
  goal_amount: number;
  current_amount: number;
  deadline: string;
  status: string;
  category?: string;
  creator_id: string;
  created_at: string;
}

interface Payment {
  id: string;
  amount: number;
  user_id: string;
  campaign_id: string;
  status: string;
  created_at: string;
}

export default function CampaignDetailPage() {
  const router = useRouter();
  const params = useParams();
  const campaignId = params.id as string;

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [donationAmount, setDonationAmount] = useState('');
  const [processing, setProcessing] = useState(false);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const userData = TokenManager.getUser();
    setUser(userData);
    fetchCampaignDetails();
    fetchPayments();
  }, [campaignId]);

  const fetchCampaignDetails = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/campaigns/${campaignId}`);
      if (response.ok) {
        const data = await response.json();
        setCampaign(data);
      } else {
        router.push('/campaigns');
      }
    } catch (error) {
      console.error('Failed to fetch campaign:', error);
      router.push('/campaigns');
    } finally {
      setLoading(false);
    }
  };

  const fetchPayments = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/payments/campaign/${campaignId}`);
      if (response.ok) {
        const data = await response.json();
        setPayments(data);
      }
    } catch (error) {
      console.error('Failed to fetch payments:', error);
    }
  };

  const handleDonate = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!user) {
      router.push('/login');
      return;
    }

    const amount = parseFloat(donationAmount);
    if (isNaN(amount) || amount <= 0) {
      alert('Please enter a valid amount');
      return;
    }

    setProcessing(true);

    try {
      const token = TokenManager.getToken();
      const response = await fetch('http://localhost:8000/api/v1/payments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          campaign_id: campaignId,
          amount: amount,
        }),
      });

      if (response.ok) {
        alert('Donation successful! Thank you for your contribution.');
        setDonationAmount('');
        fetchCampaignDetails();
        fetchPayments();
      } else {
        const error = await response.json();
        alert(error.detail || 'Donation failed');
      }
    } catch (error) {
      console.error('Donation error:', error);
      alert('Failed to process donation');
    } finally {
      setProcessing(false);
    }
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getDaysRemaining = (deadline: string) => {
    const now = new Date();
    const end = new Date(deadline);
    const diff = Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return diff > 0 ? diff : 0;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading campaign...</p>
      </div>
    );
  }

  if (!campaign) {
    return null;
  }

  const progress = calculateProgress(campaign.current_amount, campaign.goal_amount);
  const daysRemaining = getDaysRemaining(campaign.deadline);

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
            {user ? (
              <Link href="/dashboard">
                <Button variant="ghost">Dashboard</Button>
              </Link>
            ) : (
              <>
                <Link href="/login">
                  <Button variant="ghost">Sign In</Button>
                </Link>
                <Link href="/register">
                  <Button>Get Started</Button>
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-5xl">
        <Link href="/campaigns">
          <Button variant="ghost" className="mb-6">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Campaigns
          </Button>
        </Link>

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Campaign Details */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant={campaign.status === 'active' ? 'default' : 'secondary'}>
                    {campaign.status}
                  </Badge>
                  {campaign.category && (
                    <Badge variant="outline">{campaign.category}</Badge>
                  )}
                </div>
                <CardTitle className="text-3xl">{campaign.title}</CardTitle>
                <CardDescription className="text-base mt-2">
                  Created on {formatDate(campaign.created_at)}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-2">About this campaign</h3>
                  <p className="text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">
                    {campaign.description}
                  </p>
                </div>

                <Separator />

                <div>
                  <h3 className="text-lg font-semibold mb-4">Recent Donations</h3>
                  {payments.length === 0 ? (
                    <p className="text-zinc-600">No donations yet. Be the first to contribute!</p>
                  ) : (
                    <div className="space-y-3">
                      {payments.slice(0, 5).map((payment) => (
                        <div
                          key={payment.id}
                          className="flex items-center justify-between p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800"
                        >
                          <div className="flex items-center gap-3">
                            <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                              <Heart className="h-5 w-5 text-blue-600" />
                            </div>
                            <div>
                              <p className="font-medium">Anonymous Donor</p>
                              <p className="text-sm text-zinc-600">
                                {formatDate(payment.created_at)}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="font-bold text-green-600">
                              {formatCurrency(payment.amount)}
                            </p>
                            <Badge variant="outline" className="text-xs">
                              {payment.status}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Donation Sidebar */}
          <div className="space-y-6">
            {/* Stats Card */}
            <Card>
              <CardContent className="pt-6 space-y-6">
                <div>
                  <div className="flex justify-between items-baseline mb-2">
                    <span className="text-3xl font-bold text-blue-600">
                      {formatCurrency(campaign.current_amount)}
                    </span>
                    <span className="text-sm text-zinc-600">
                      of {formatCurrency(campaign.goal_amount)}
                    </span>
                  </div>
                  <Progress value={progress} className="h-3" />
                  <p className="text-sm text-zinc-600 mt-2">
                    {progress.toFixed(1)}% funded
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-zinc-600">
                      <Users className="h-4 w-4" />
                      <span className="text-sm">Backers</span>
                    </div>
                    <p className="text-2xl font-bold">{payments.length}</p>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-zinc-600">
                      <Calendar className="h-4 w-4" />
                      <span className="text-sm">Days left</span>
                    </div>
                    <p className="text-2xl font-bold">{daysRemaining}</p>
                  </div>
                </div>

                <Separator />

                {/* Donation Form */}
                {campaign.status === 'active' ? (
                  <form onSubmit={handleDonate} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="amount">Donation Amount</Label>
                      <div className="relative">
                        <DollarSign className="absolute left-3 top-3 h-4 w-4 text-zinc-400" />
                        <Input
                          id="amount"
                          type="number"
                          step="0.01"
                          min="1"
                          placeholder="25.00"
                          className="pl-10"
                          value={donationAmount}
                          onChange={(e) => setDonationAmount(e.target.value)}
                          required
                          disabled={processing}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      {[25, 50, 100].map((amount) => (
                        <Button
                          key={amount}
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setDonationAmount(amount.toString())}
                          disabled={processing}
                        >
                          ${amount}
                        </Button>
                      ))}
                    </div>
                    <Button type="submit" className="w-full" size="lg" disabled={processing}>
                      {processing ? 'Processing...' : 'Donate Now'}
                    </Button>
                    {!user && (
                      <p className="text-xs text-center text-zinc-600">
                        You need to <Link href="/login" className="text-blue-600 hover:underline">sign in</Link> to donate
                      </p>
                    )}
                  </form>
                ) : (
                  <div className="text-center py-4">
                    <Badge variant="secondary" className="text-base px-4 py-2">
                      Campaign Ended
                    </Badge>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Campaign Info Card */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Campaign Info</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-600">Deadline</span>
                  <span className="font-medium">{formatDate(campaign.deadline)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-600">Status</span>
                  <Badge variant={campaign.status === 'active' ? 'default' : 'secondary'}>
                    {campaign.status}
                  </Badge>
                </div>
                {campaign.category && (
                  <div className="flex justify-between">
                    <span className="text-zinc-600">Category</span>
                    <span className="font-medium">{campaign.category}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
