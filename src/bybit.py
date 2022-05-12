import json
import time

from orderbooks.l2 import L2Lob
from orderbooks.orderbook import LobUpdateError
from source_connectors.kafka_consumer import KafkaConsumer 
from sink_connectors.kafka_producer import KafkaProducer

def enrich_quote(quote, lob_event, last_update_timestamp):
    quote['last_update_timestamp'] = last_update_timestamp
    quote['event_no'] = lob_event['event_no']
    quote['quote_no'] = lob_event['quote_no']
    quote['event_timestamp'] = lob_event['send_timestamp']
    quote['send_timestamp'] = str(int(time.time() * 10**3))

def main():
    consumer = KafkaConsumer('bybit-normalised')
    producer = KafkaProducer('bybit-L1')
    orderbook = L2Lob()
    current_quote = None
    current_event_no = -1
    last_update_timestamp = "-1"
    prev_event = None
    while True:
        message = consumer.consume()
        if not message is None:
            lob_event = json.loads(message)
            if 'quote_no' in lob_event.keys():
                # Only produce if L1 quote has updated
                quote = orderbook.book_top()
                if current_event_no != lob_event['event_no'] and \
                        (current_quote is None or current_quote != quote) and \
                        not prev_event is None:
                    enrich_quote(quote, prev_event, last_update_timestamp)
                    producer.produce(str(prev_event['event_no']), quote)
                    last_update_timestamp = str(int(time.time() * 10**3))
                    current_event_no = lob_event['event_no']
                    current_quote = orderbook.book_top()

                try:
                    orderbook.handle_event(lob_event)
                except LobUpdateError:
                    # No snapshot, so need to build orderbook asymptotically.
                    pass 
                prev_event = lob_event

if __name__ == "__main__":
    main()