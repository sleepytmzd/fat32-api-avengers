'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Heart, ArrowLeft, Target, Calendar, FileText, DollarSign } from 'lucide-react';
import { TokenManager } from '@/lib/api';

export default function CreateCampaignPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    goal_amount: '',
    deadline: '',
    category: '',
  });

  useEffect(() => {
    const token = TokenManager.getToken();
    const userData = TokenManager.getUser();

    if (!token || !userData) {
      router.push('/login');
      return;
    }

    setUser(userData);
  }, [router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Validate goal amount
    const goalAmount = parseFloat(formData.goal_amount);
    if (isNaN(goalAmount) || goalAmount <= 0) {
      setError('Please enter a valid goal amount');
      setLoading(false);
      return;
    }

    // Validate deadline is in the future
    const deadlineDate = new Date(formData.deadline);
    const now = new Date();
    if (deadlineDate <= now) {
      setError('Deadline must be in the future');
      setLoading(false);
      return;
    }

    try {
      const token = TokenManager.getToken();
      const response = await fetch('http://localhost:8000/api/v1/campaigns', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: formData.title,
          description: formData.description,
          goal_amount: goalAmount,
          deadline: formData.deadline,
          category: formData.category || undefined,
        }),
      });

      if (response.ok) {
        const campaign = await response.json();
        router.push(`/campaigns/${campaign.id}`);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create campaign');
      }
    } catch (err) {
      console.error('Error creating campaign:', err);
      setError('Failed to create campaign. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
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
            <Link href="/dashboard">
              <Button variant="ghost">Dashboard</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-3xl">
        <Link href="/campaigns">
          <Button variant="ghost" className="mb-6">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Campaigns
          </Button>
        </Link>

        <Card>
          <CardHeader>
            <CardTitle className="text-3xl">Start a New Campaign</CardTitle>
            <CardDescription>
              Create a fundraising campaign and share your cause with the community
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="title">Campaign Title *</Label>
                <div className="relative">
                  <FileText className="absolute left-3 top-3 h-4 w-4 text-zinc-400" />
                  <Input
                    id="title"
                    name="title"
                    placeholder="Give your campaign a clear, descriptive title"
                    className="pl-10"
                    value={formData.title}
                    onChange={handleChange}
                    required
                    disabled={loading}
                    maxLength={200}
                  />
                </div>
                <p className="text-xs text-zinc-500">
                  A compelling title helps attract more supporters
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Campaign Description *</Label>
                <Textarea
                  id="description"
                  name="description"
                  placeholder="Tell your story. Explain what you're raising funds for and why it matters..."
                  rows={8}
                  value={formData.description}
                  onChange={handleChange}
                  required
                  disabled={loading}
                  className="resize-none"
                />
                <p className="text-xs text-zinc-500">
                  Share the details of your cause and how donations will be used
                </p>
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="goal_amount">Funding Goal (USD) *</Label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-3 h-4 w-4 text-zinc-400" />
                    <Input
                      id="goal_amount"
                      name="goal_amount"
                      type="number"
                      step="0.01"
                      min="1"
                      placeholder="5000.00"
                      className="pl-10"
                      value={formData.goal_amount}
                      onChange={handleChange}
                      required
                      disabled={loading}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="deadline">Campaign Deadline *</Label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-3 h-4 w-4 text-zinc-400" />
                    <Input
                      id="deadline"
                      name="deadline"
                      type="date"
                      className="pl-10"
                      value={formData.deadline}
                      onChange={handleChange}
                      required
                      disabled={loading}
                      min={new Date().toISOString().split('T')[0]}
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="category">Category (Optional)</Label>
                <Select
                  value={formData.category}
                  onValueChange={(value) => setFormData({ ...formData, category: value })}
                  disabled={loading}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="medical">Medical</SelectItem>
                    <SelectItem value="education">Education</SelectItem>
                    <SelectItem value="emergency">Emergency Relief</SelectItem>
                    <SelectItem value="community">Community</SelectItem>
                    <SelectItem value="environment">Environment</SelectItem>
                    <SelectItem value="animals">Animals</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900 rounded-lg p-4">
                <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                  Before you submit:
                </h4>
                <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-disc list-inside">
                  <li>Make sure your title is clear and compelling</li>
                  <li>Provide detailed information about your cause</li>
                  <li>Set a realistic funding goal</li>
                  <li>Choose an appropriate deadline for your campaign</li>
                </ul>
              </div>

              <div className="flex gap-4">
                <Button
                  type="button"
                  variant="outline"
                  className="flex-1"
                  onClick={() => router.back()}
                  disabled={loading}
                >
                  Cancel
                </Button>
                <Button type="submit" className="flex-1" disabled={loading}>
                  {loading ? 'Creating Campaign...' : 'Create Campaign'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
