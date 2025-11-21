import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Heart, Users, TrendingUp, Shield } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white dark:from-zinc-950 dark:to-zinc-900">
      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="flex justify-center mb-6">
          <Heart className="h-16 w-16 text-blue-600 fill-blue-600" />
        </div>
        <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          CareForAll
        </h1>
        <p className="text-xl md:text-2xl text-zinc-600 dark:text-zinc-400 mb-8 max-w-2xl mx-auto">
          Empowering communities through transparent and secure fundraising
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/campaigns">
            <Button size="lg" className="h-14 px-8 text-lg">
              Browse Campaigns
            </Button>
          </Link>
          <Link href="/campaigns/create">
            <Button size="lg" variant="outline" className="h-14 px-8 text-lg">
              Start a Campaign
            </Button>
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">Why Choose CareForAll?</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-white dark:bg-zinc-800 p-8 rounded-lg shadow-md">
            <Shield className="h-12 w-12 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold mb-3">Secure Payments</h3>
            <p className="text-zinc-600 dark:text-zinc-400">
              Advanced payment processing with full transparency and security
            </p>
          </div>
          <div className="bg-white dark:bg-zinc-800 p-8 rounded-lg shadow-md">
            <Users className="h-12 w-12 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold mb-3">Community Driven</h3>
            <p className="text-zinc-600 dark:text-zinc-400">
              Join thousands of donors making a real difference in communities
            </p>
          </div>
          <div className="bg-white dark:bg-zinc-800 p-8 rounded-lg shadow-md">
            <TrendingUp className="h-12 w-12 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold mb-3">Real-time Tracking</h3>
            <p className="text-zinc-600 dark:text-zinc-400">
              Monitor campaign progress and receive instant notifications
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-12 text-white">
          <h2 className="text-3xl font-bold mb-4">Ready to Make a Difference?</h2>
          <p className="text-xl mb-8 opacity-90">Join our community of generous donors today</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/register">
              <Button size="lg" variant="secondary" className="h-14 px-8 text-lg">
                Get Started
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline" className="h-14 px-8 text-lg bg-white/10 hover:bg-white/20 text-white border-white">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
