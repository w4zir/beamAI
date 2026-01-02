import { useState, useEffect } from 'react'
import { Loader2, Sparkles } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { getRecommendations, RecommendResult } from '../api/recommend'
import { supabase } from '../api/supabase'
import { trackEvent } from '../api/events'

interface Product {
  id: string
  name: string
  description: string
  category: string
  price: number
}

export default function Recommendations() {
  const [results, setResults] = useState<RecommendResult[]>([])
  const [products, setProducts] = useState<Record<string, Product>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)

  // Get current user ID
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      const id = data.session?.user?.id || null
      setUserId(id)
      
      if (id) {
        loadRecommendations(id)
      } else {
        setError('Please log in to view recommendations')
        setLoading(false)
      }
    })
  }, [])

  // Fetch product details for recommendations and track view events
  useEffect(() => {
    if (results.length === 0) {
      setProducts({})
      return
    }

    const fetchProductDetails = async () => {
      const productIds = results.map(r => r.product_id)
      
      try {
        const { data, error } = await supabase
          .from('products')
          .select('id, name, description, category, price')
          .in('id', productIds)

        if (error) throw error

        const productMap: Record<string, Product> = {}
        data?.forEach(product => {
          productMap[product.id] = product as Product
        })
        setProducts(productMap)

        // Track view events for all products in recommendations
        if (userId) {
          productIds.forEach(productId => {
            trackEvent({
              userId,
              productId,
              eventType: 'view',
              source: 'recommendation',
            }).catch(err => console.error('Failed to track view event:', err))
          })
        }
      } catch (err) {
        console.error('Error fetching product details:', err)
      }
    }

    fetchProductDetails()
  }, [results, userId])

  const loadRecommendations = async (id: string) => {
    setLoading(true)
    setError(null)
    setResults([])

    try {
      const recommendations = await getRecommendations(id, 10)
      setResults(recommendations)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recommendations')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <main className="max-w-6xl mx-auto p-6">
        <div className="text-center py-12">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-gray-600 mb-4" />
          <p className="text-muted-foreground">Loading recommendations...</p>
        </div>
      </main>
    )
  }

  return (
    <main className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2 flex items-center gap-2">
          <Sparkles className="h-8 w-8" />
          Recommendations
        </h1>
        <p className="text-muted-foreground">Personalized product recommendations for you</p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-4 bg-destructive/10 text-destructive rounded-md">
          {error}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="mb-4">
          <p className="text-sm text-muted-foreground">
            Found {results.length} recommendation{results.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}

      {/* Results Grid */}
      {results.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {results.map((result) => {
            const product = products[result.product_id]
            return (
              <Card 
                key={result.product_id} 
                className="hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => {
                  if (userId) {
                    trackEvent({
                      userId,
                      productId: result.product_id,
                      eventType: 'view',
                      source: 'recommendation',
                    }).catch(err => console.error('Failed to track click event:', err))
                  }
                }}
              >
                <CardHeader>
                  <CardTitle className="text-lg">
                    {product?.name || 'Loading...'}
                  </CardTitle>
                  <CardDescription>
                    {product?.category && (
                      <Badge variant="secondary" className="mr-2">
                        {product.category}
                      </Badge>
                    )}
                    {product?.price && (
                      <span className="text-sm font-semibold">
                        ${product.price.toFixed(2)}
                      </span>
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {product?.description && (
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                      {product.description}
                    </p>
                  )}
                  <div className="flex justify-between items-center text-xs text-muted-foreground">
                    <span>Score: {result.score.toFixed(3)}</span>
                    {result.reason && (
                      <span className="truncate max-w-[200px]" title={result.reason}>
                        {result.reason}
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : (
        !loading && (
          <div className="text-center py-12">
            <Sparkles className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No recommendations available</p>
          </div>
        )
      )}
    </main>
  )
}

