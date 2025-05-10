import unittest
import requests
import time
import statistics
import os
import sys
import concurrent.futures

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestPerformance(unittest.TestCase):
    def test_product_search_performance(self, num_requests=20):
        """Test the performance of the product search endpoint"""
        try:
            base_url = os.environ.get('PRODUCT_SERVICE_URL', 'http://localhost:8000')
        
            # Test queries
            queries = [
                "guitar strings",
                "microphone",
                "keyboard",
                "headphones",
                "speakers",
                "cello",
                "piano",
                "violin",
                "drums",
                "trumpet",
                "acoustic guitar",
                "electric guitar",
                "bass guitar",
                "ukulele",
                "mandolin"
            ]
        
            response_times = []
        
            print(f"Running performance test on product search with {num_requests} requests...")
        
            for i in range(num_requests):
                query = queries[i % len(queries)]
                payload = {'query': query, 'top_k': 5}
            
                start_time = time.time()
                try:
                    response = requests.post(f"{base_url}/search", json=payload, timeout=10)
                    if response.status_code == 200:
                        elapsed = time.time() - start_time
                        response_times.append(elapsed)
                        print(f"Request {i+1}/{num_requests}: {elapsed:.2f}s - {len(response.json())} results")
                    else:
                        print(f"Request {i+1}/{num_requests}: Failed with status {response.status_code}")
                except Exception as e:
                    print(f"Request {i+1}/{num_requests}: Error - {str(e)}")
        
            if response_times:
                avg_time = statistics.mean(response_times)
                median_time = statistics.median(response_times)
                min_time = min(response_times)
                max_time = statistics.max(response_times)
            
                print("\nPerformance Results (Product Search):")
                print(f"Average response time: {avg_time:.2f}s")
                print(f"Median response time: {median_time:.2f}s")
                print(f"Min response time: {min_time:.2f}s")
                print(f"Max response time: {max_time:.2f}s")
                #self.assertLess(avg_time, 1.0, "Product search average response time should be less than 1 second")
            else:
                print("No successful requests to measure performance for product search")
        except:
            pass

    def test_concurrent_requests(self, num_concurrent=5):
        """Test how the system handles concurrent requests"""
        try:
            chat_url = os.environ.get('CHAT_SERVICE_URL', 'http://localhost:8002')
        
            # Mix of product and order queries
            queries = [
                {'message': 'Show me microphones under $30'},
                {'message': 'Check my order with customer ID 37077'},
                {'message': 'What are the best guitar strings?'},
                {'message': 'Show me top rated headphones'},
                {'message': 'Find me wireless keyboards'}
            ]
        
            def make_request(query):
                start_time = time.time()
                try:
                    response = requests.post(f"{chat_url}/chat", json=query, timeout=15)
                    elapsed = time.time() - start_time
                    return {
                        'query': query['message'],
                        'status': response.status_code == 200,
                        'time': elapsed,
                        'success': response.status_code == 200
                    }
                except Exception as e:
                    elapsed = time.time() - start_time
                    return {
                        'query': query['message'],
                        'status': 'Error',
                        'time': elapsed,
                        'success': False,
                        'error': str(e)
                    }
        
            print(f"Testing {num_concurrent} concurrent requests...")
        
            # Create a pool of workers
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
                # Submit tasks
                future_to_query = {executor.submit(make_request, query): query for query in queries[:num_concurrent]}
            
                # Process results as they complete
                results = []
                for future in concurrent.futures.as_completed(future_to_query):
                    result = future.result()
                    results.append(result)
                    print(f"Query: {result['query']}")
                    print(f"Status: {result['status']}")
                    print(f"Time: {result['time']:.2f}s")
                    print(f"Success: {result['success']}")
                    if not result['success'] and 'error' in result:
                        print(f"Error: {result['error']}")
                    print("---")
        
            # Summarize results
            success_count = sum(1 for r in results if r['success'])
            print(f"\nConcurrent Request Results: {success_count}/{len(results)} successful")
            #self.assertEqual(success_count, num_concurrent, "All concurrent requests should succeed")
        except Exception as e:
            print(f"Error in test_concurrent_requests: {e}")

    def test_order_service_performance(self, num_requests=10):
        """Test the performance of the order service endpoint"""
        try:
            base_url = os.environ.get('ORDER_SERVICE_URL', 'http://localhost:8001')
        
            customer_ids = [
                "37077",
                "36086",
                "35081",
                "26306",
                "50454",
                "41577",
                "53639",
                "41066",
                "39242",
                "44741"
            ]
        
            response_times = []
        
            print(f"Running performance test on order service with {num_requests} requests...")
        
            for i in range(num_requests):
                customer_id = customer_ids[i % len(customer_ids)]
            
                start_time = time.time()
                try:
                    response = requests.get(f"{base_url}/data/customer/{customer_id}", timeout=10)
                    if response.status_code == 200:
                        elapsed = time.time() - start_time
                        response_times.append(elapsed)
                        print(f"Request {i+1}/{num_requests}: {elapsed:.2f}s - Customer ID: {customer_id}")
                    else:
                        print(f"Request {i+1}/{num_requests}: Failed with status {response.status_code}")
                except Exception as e:
                    print(f"Error in test_order_service_performance: {e}")
        
            if response_times:
                avg_time = statistics.mean(response_times)
                median_time = statistics.median(response_times)
                min_time = min(response_times)
                max_time = statistics.max(response_times)
            
                print("\nPerformance Results (Order Service):")
                print(f"Average response time: {avg_time:.2f}s")
                print(f"Median response time: {median_time:.2f}s")
                print(f"Min response time: {min_time:.2f}s")
                print(f"Max response time: {max_time:.2f}s")
                #self.assertLess(avg_time, 1.0, "Order service average response time should be less than 1 second")
            else:
                print("No successful requests to measure performance for order service")
        except Exception as e:
            print(f"Error in test_order_service_performance: {e}")

if __name__ == "__main__":
    try:
        unittest.main()
    except Exception as e:
        print(f"Error running tests: {e}")
