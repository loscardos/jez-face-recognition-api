"""
Laravel Database Synchronization
Handles syncing face data between Face Recognition service and Laravel database.

Database: jez_erp | Table: users (configured in Laravel User model) | Column: u_face
See DATABASE_CONFIG.md for details about table configuration.

Note: Communicates via Laravel API endpoints, not direct database queries.
"""
import json
import logging
import os
from typing import Dict, List, Optional
import requests
from config import config

logger = logging.getLogger(__name__)

class LaravelSync:
    """Synchronize face data with Laravel backend"""
    
    def __init__(self):
        self.api_url = config.LARAVEL_API_URL
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        # Add Bearer token if available
        if token := os.getenv('LARAVEL_API_TOKEN'):
            self.headers['Authorization'] = f'Bearer {token}'
    
    def get_users_face_data(self) -> Dict[int, Dict]:
        """
        Fetch all users' face data from Laravel
        Returns: {user_id: {'encodings': [...], 'samples_count': ...}}
        """
        try:
            response = requests.get(
                f'{self.api_url}/v1/admin/face-data/all',
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') != 'success':
                logger.warning(f"Laravel returned error: {data.get('message')}")
                return {}
            
            # Parse face data
            users_face_data = {}
            for user_data in data.get('data', []):
                user_id = user_data.get('id')
                face_data_json = user_data.get('u_face')
                
                if user_id and face_data_json:
                    try:
                        face_data = json.loads(face_data_json)
                        
                        # Handle different data formats
                        samples = []
                        if 'samples' in face_data:
                            # New format: {samples: [[...], [...]]}
                            samples = face_data.get('samples', [])
                        elif 'descriptors' in face_data:
                            # Alternative format: {descriptors: [[...], [...]]}
                            samples = face_data.get('descriptors', [])
                        elif isinstance(face_data, list):
                            # Direct array format
                            samples = face_data
                        
                        # Filter valid samples (must be list of floats)
                        valid_samples = []
                        for sample in samples:
                            if isinstance(sample, list) and len(sample) > 0:
                                valid_samples.append(sample)
                            elif isinstance(sample, dict) and 'descriptor' in sample:
                                valid_samples.append(sample['descriptor'])
                        
                        if valid_samples:
                            users_face_data[user_id] = {
                                'samples': valid_samples,
                                'samples_count': len(valid_samples),
                                'model': face_data.get('model', 'unknown'),
                                'registered_at': face_data.get('registered_at')
                            }
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse face data for user {user_id}")
                        continue
            
            logger.info(f"Loaded face data for {len(users_face_data)} users")
            return users_face_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch face data from Laravel: {str(e)}")
            return {}
    
    def get_user_face_data(self, user_id: int) -> Optional[Dict]:
        """Fetch a specific user's face data from Laravel"""
        try:
            response = requests.get(
                f'{self.api_url}/v1/mobile/face',
                headers={**self.headers, 'Authorization': f'Bearer user_{user_id}'},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') != 'success':
                return None
            
            return data.get('data')
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch face data for user {user_id}: {str(e)}")
            return None
    
    def store_face_descriptor(self, user_id: int, descriptor: List[float], 
                             mode: str = 'registration') -> bool:
        """
        Store face descriptor in Laravel
        mode: 'registration' or 'photo'
        """
        try:
            payload = {
                'face_descriptor': descriptor,
                'mode': mode,
                'descriptor_count': 1
            }
            
            response = requests.post(
                f'{self.api_url}/v1/mobile/face',
                json=payload,
                headers={**self.headers, 'Authorization': f'Bearer user_{user_id}'},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('status') == 'success'
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to store face descriptor for user {user_id}: {str(e)}")
            return False
    
    def get_user_details(self, user_id: int) -> Dict:
        """
        Get user details from Laravel
        Returns: {'name': str, 'email': str, 'phone': str}
        """
        try:
            response = requests.get(
                f'{self.api_url}/v1/admin/users/{user_id}',
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'success':
                user = data.get('data', {})
                return {
                    'name': user.get('u_name', 'Unknown'),
                    'email': user.get('u_email', ''),
                    'phone': user.get('u_phone', ''),
                }
            
            return {'name': 'Unknown', 'email': '', 'phone': ''}
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch user details for {user_id}: {str(e)}")
            return {'name': 'Unknown', 'email': '', 'phone': ''}

import os
laravel_sync = LaravelSync()
