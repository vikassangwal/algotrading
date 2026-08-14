import os
from app.brokers.factory import BrokerFactory
from app.db import Base, db_engine, SessionLocal
from app.routers.brokers_api import BrokerConnection

def test_kotak_neo():
    Base.metadata.create_all(bind=db_engine, tables=[BrokerConnection.__table__])
    
    broker_name = "kotak_neo"
    api_key = "+919509374991,X08WI,258008,7F7MKHWNW7CETUB2YYJPD6LVPA"
    api_secret = "dummy_token"

    print(f"Testing broker: {broker_name}...")
    try:
        b = BrokerFactory.get_broker(
            broker_name,
            api_key=api_key,
            api_secret=api_secret
        )
        print("Success! Broker initialized:", b)
        
        # Test connecting
        connected = b.connect()
        print("Connected:", connected)
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    test_kotak_neo()
