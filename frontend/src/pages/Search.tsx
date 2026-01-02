import { useState, useEffect } from 'react'
import { Search as SearchIcon, Loader2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { searchProducts, SearchResult } from '../api/search'
import { supabase } from '../api/supabase'
import { trackEvent } from '../api/events'

interface Product {
  id: string
  name: string
  description: string
  category: string
  price: number
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [products, setProducts] = useState<Record<string, Product>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)

  // Get current user ID
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setUserId(data.session?.user?.id || null)
    })
  }, [])

  // Fetch product details for search results and track view events
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

        // Track view events for all products in search results
        if (userId) {
          productIds.forEach(productId => {
            trackEvent({
              userId,
              productId,
              eventType: 'view',
              source: 'search',
            }).catch(err => console.error('Failed to track view event:', err))
          })
        }
      } catch (err) {
        console.error('Error fetching product details:', err)
      }
    }

    fetchProductDetails()
  }, [results, userId])

  const handleSearch = async () => {
    if (!query.trim()) {
      setError('Please enter a search query')
      return
    }

    setLoading(true)
    setError(null)
    setResults([])

    try {
      const searchResults = await searchProducts(query.trim(), userId || undefined, 10)
      setResults(searchResults)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <main className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Search Products</h1>
        <p className="text-muted-foreground">Find products using keyword search</p>
      </div>

      {/* Search Input */}
      <div className="mb-6 flex gap-2">
        <div className="flex-1 relative">
          <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-5 w-5" />
          <Input
            type="text"
            placeholder="Search for products..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="pl-10"
          />
        </div>
        <Button onClick={handleSearch} disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Searching...
            </>
          ) : (
            'Search'
          )}
        </Button>
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
            Found {results.length} result{results.length !== 1 ? 's' : ''}
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
                      source: 'search',
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
        !loading && query && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No results found</p>
          </div>
        )
      )}

      {/* Empty State */}
      {!loading && !query && results.length === 0 && (
        <div className="text-center py-12">
          <SearchIcon className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Enter a search query to find products</p>
        </div>
      )}
    </main>
  )
}

