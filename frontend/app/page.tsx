"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"

const API_BASE = ""

export default function Home() {
  const [githubToken, setGithubToken] = useState("")
  const [openaiKey, setOpenaiKey] = useState("")
  const [webhookSecret, setWebhookSecret] = useState("")
  const [webhookUrl, setWebhookUrl] = useState("")
  const [jobs, setJobs] = useState<any[]>([])

  useEffect(() => {
    fetchJobs()
    const interval = setInterval(fetchJobs, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchJobs = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/jobs`)
      if (response.ok) {
        const data = await response.json()
        setJobs(data)
      }
    } catch (error) {
      console.error("Failed to fetch jobs:", error)
    }
  }

  const handleSaveConfig = async () => {
    const response = await fetch(`${API_BASE}/api/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ githubToken, openaiKey, webhookSecret }),
    })
    if (response.ok) {
      alert("Configuration saved successfully!")
    }
  }

  const handleGetWebhookUrl = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/webhook-url`)
      if (response.ok) {
        const data = await response.json()
        setWebhookUrl(data.webhookUrl)
      }
    } catch (error) {
      console.error("Failed to fetch webhook URL:", error)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            GitHub AI Automation Tool
          </h1>
          <p className="text-gray-600 dark:text-gray-300">
            Automate code changes with AI-powered GitHub issue responses
          </p>
        </div>

        <Tabs defaultValue="config" className="max-w-4xl mx-auto">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="config">Configuration</TabsTrigger>
            <TabsTrigger value="webhook">Webhook Setup</TabsTrigger>
            <TabsTrigger value="jobs">Job History</TabsTrigger>
          </TabsList>

          <TabsContent value="config">
            <Card>
              <CardHeader>
                <CardTitle>API Configuration</CardTitle>
                <CardDescription>
                  Configure your GitHub and OpenAI API credentials
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="github-token">GitHub Personal Access Token</Label>
                  <Input
                    id="github-token"
                    type="password"
                    placeholder="ghp_xxxxxxxxxxxx"
                    value={githubToken}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGithubToken(e.target.value)}
                  />
                  <p className="text-sm text-muted-foreground">
                    Required permissions: repo, workflow
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="openai-key">OpenAI API Key</Label>
                  <Input
                    id="openai-key"
                    type="password"
                    placeholder="sk-xxxxxxxxxxxx"
                    value={openaiKey}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setOpenaiKey(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="webhook-secret">Webhook Secret (Optional)</Label>
                  <Input
                    id="webhook-secret"
                    type="password"
                    placeholder="your_webhook_secret"
                    value={webhookSecret}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setWebhookSecret(e.target.value)}
                  />
                  <p className="text-sm text-muted-foreground">
                    For enhanced security, set this as the secret in your GitHub webhook
                  </p>
                </div>

                <Button onClick={handleSaveConfig} className="w-full">
                  Save Configuration
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="webhook">
            <Card>
              <CardHeader>
                <CardTitle>GitHub Webhook Setup</CardTitle>
                <CardDescription>
                  Configure your repository to send events to this tool
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Webhook URL</Label>
                  <div className="flex gap-2">
                    <Input
                      value={webhookUrl}
                      readOnly
                      placeholder="Click 'Get Webhook URL' to generate"
                    />
                    <Button onClick={handleGetWebhookUrl}>Get Webhook URL</Button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Setup Instructions</Label>
                  <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                    <li>Go to your GitHub repository settings</li>
                    <li>Navigate to Webhooks and click "Add webhook"</li>
                    <li>Paste the webhook URL above</li>
                    <li>If you set a webhook secret in Configuration, paste it in the Secret field</li>
                    <li>Content type: application/json</li>
                    <li>Select "Let me select individual events"</li>
                    <li>Check "Issue comments" event only</li>
                    <li>Click "Add webhook"</li>
                  </ol>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="jobs">
            <Card>
              <CardHeader>
                <CardTitle>Job History</CardTitle>
                <CardDescription>
                  Track AI automation tasks and their status
                </CardDescription>
              </CardHeader>
              <CardContent>
                {jobs.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No jobs yet. Comment @my-tool on a GitHub issue to get started!
                  </div>
                ) : (
                  <div className="space-y-3">
                    {jobs.map((job) => (
                      <div key={job.id} className="border rounded-lg p-4">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">{job.repo}</p>
                            <p className="text-sm text-muted-foreground">
                              Issue #{job.issueNumber}: {job.issueTitle}
                            </p>
                          </div>
                          <Badge
                            variant={
                              job.status === "completed"
                                ? "default"
                                : job.status === "failed"
                                ? "destructive"
                                : "secondary"
                            }
                          >
                            {job.status}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
