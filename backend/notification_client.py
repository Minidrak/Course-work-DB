import json
import time
from redis_config import get_pubsub

def listen_for_notifications():
    pubsub = get_pubsub()
    
    # подписываемся на все каналы
    pubsub.subscribe('artworks', 'artwork_reviews', 'orders')
    
    print("Listening for notifications...")
    
    while True:
        message = pubsub.get_message()
        if message and message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                channel = message['channel']
                
                print(f"\nNew notification on channel '{channel}':")
                print(f"Type: {data.get('type')}")
                
                if data.get('type') == 'new_artwork':
                    print(f"New artwork added: {data.get('title')} (ID: {data.get('artwork_id')})")
                    print(f"Price: ${data.get('price')}")
                
                elif data.get('type') == 'new_review':
                    print(f"New review for artwork {data.get('artwork_id')}")
                    print(f"Rating: {data.get('rating')}/5")
                
                elif data.get('type') == 'new_order':
                    print(f"New order created (ID: {data.get('order_id')})")
                    print(f"Artwork ID: {data.get('artwork_id')}")
                    print(f"Quantity: {data.get('quantity')}")
                
            except json.JSONDecodeError:
                print("Error decoding message")
            except Exception as e:
                print(f"Error processing message: {str(e)}")
        
        time.sleep(0.1)

if __name__ == '__main__':
    listen_for_notifications() 