import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

def split_conversations_by_time(input_file, output_dir):
    """
    Split conversations.json into time-based chunks:
    - last-3-months.json
    - 3-6-months.json
    - 6-12-months.json
    - older.json
    """
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Load full conversations
    print(f"Loading {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {input_file}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {input_file}: {e}")
        return
    
    # Handle different data structures
    if isinstance(data, dict):
        # ChatGPT format: {"conversations": [...]} or similar
        if 'conversations' in data:
            conversations = data['conversations']
        elif 'items' in data:
            conversations = data['items']
        else:
            # Try to find list-like structure
            conversations = [v for v in data.values() if isinstance(v, list)]
            conversations = conversations[0] if conversations else []
    elif isinstance(data, list):
        conversations = data
    else:
        print(f"❌ Error: Unexpected data structure in {input_file}")
        return
    
    print(f"Total conversations: {len(conversations)}")
    
    # Calculate time boundaries (use UTC to avoid timezone issues)
    now = datetime.now(timezone.utc)
    three_months_ago = now - timedelta(days=90)
    six_months_ago = now - timedelta(days=180)
    twelve_months_ago = now - timedelta(days=365)
    
    # Buckets for conversations
    buckets = {
        'last-3-months': [],
        '3-6-months': [],
        '6-12-months': [],
        'older': []
    }
    
    # Sort conversations into buckets
    for conv in conversations:
        # Get conversation timestamp (try multiple field names)
        timestamp = None
        for field in ['create_time', 'created_at', 'timestamp', 'created', 'date', 'updated_at', 'update_time']:
            if field in conv:
                timestamp = conv[field]
                break
        
        # Also check nested structures
        if not timestamp and 'metadata' in conv:
            metadata = conv['metadata']
            for field in ['create_time', 'created_at', 'timestamp', 'created', 'date']:
                if field in metadata:
                    timestamp = metadata[field]
                    break
        
        if not timestamp:
            # If no timestamp, put in 'older'
            buckets['older'].append(conv)
            continue
        
        # Parse timestamp (handle different formats)
        conv_date = None
        if isinstance(timestamp, (int, float)):
            # Unix timestamp (seconds or milliseconds)
            if timestamp > 1e12:  # Likely milliseconds
                conv_date = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            else:  # Likely seconds
                conv_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        elif isinstance(timestamp, str):
            # String timestamp
            try:
                # Try ISO format
                conv_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                # Ensure it's timezone-aware
                if conv_date.tzinfo is None:
                    conv_date = conv_date.replace(tzinfo=timezone.utc)
            except:
                try:
                    # Try common formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                        try:
                            conv_date = datetime.strptime(timestamp, fmt)
                            # Make it timezone-aware (assume UTC)
                            conv_date = conv_date.replace(tzinfo=timezone.utc)
                            break
                        except:
                            continue
                except:
                    pass
        
        if not conv_date:
            buckets['older'].append(conv)
            continue
        
        # Normalize to UTC if timezone-aware
        if conv_date.tzinfo is not None:
            conv_date = conv_date.astimezone(timezone.utc)
        else:
            # If naive, assume UTC
            conv_date = conv_date.replace(tzinfo=timezone.utc)
        
        # Sort into appropriate bucket
        if conv_date >= three_months_ago:
            buckets['last-3-months'].append(conv)
        elif conv_date >= six_months_ago:
            buckets['3-6-months'].append(conv)
        elif conv_date >= twelve_months_ago:
            buckets['6-12-months'].append(conv)
        else:
            buckets['older'].append(conv)
    
    # Minimize each conversation (keep only essential data)
    def minimize_conv(conv):
        """Keep only messages and timestamp, strip metadata"""
        messages = []
        
        # Extract messages from conversation
        # Try ChatGPT format first (nested mapping)
        if 'mapping' in conv:
            msg_list = conv['mapping']
            if isinstance(msg_list, dict):
                for node_id, node in msg_list.items():
                    message = node.get('message')
                    if message and message.get('content'):
                        content_parts = message['content'].get('parts', [])
                        if content_parts:
                            # Join parts intelligently
                            content = ' '.join(str(part) for part in content_parts if part)
                            if content.strip():
                                messages.append({
                                    'role': message.get('author', {}).get('role', 'unknown'),
                                    'content': content[:5000]  # Limit content length
                                })
        
        # Try Claude format or standard format
        elif 'messages' in conv:
            msg_list = conv['messages']
            if isinstance(msg_list, list):
                for msg in msg_list:
                    content = msg.get('content') or msg.get('text') or ''
                    if content:
                        messages.append({
                            'role': msg.get('role', msg.get('author', 'unknown')),
                            'content': str(content)[:5000]  # Limit content length
                        })
        
        # Try other common structures
        elif 'items' in conv:
            for item in conv['items']:
                if isinstance(item, dict) and 'content' in item:
                    messages.append({
                        'role': item.get('role', 'unknown'),
                        'content': str(item['content'])[:5000]
                    })
        
        return {
            'messages': messages,
            'timestamp': conv.get('create_time') or conv.get('created_at') or conv.get('timestamp'),
            'title': str(conv.get('title', ''))[:100]  # Keep short title for context
        }
    
    # Save each bucket
    total_size = 0
    for bucket_name, conversations in buckets.items():
        if not conversations:
            print(f"  {bucket_name}: 0 conversations (skipped)")
            continue
        
        # Minimize conversations
        minimal = [minimize_conv(conv) for conv in conversations]
        
        # Save to file
        output_file = output_path / f"{bucket_name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(minimal, f, indent=2, ensure_ascii=False)
        
        # Calculate file size
        size_mb = output_file.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f"  {bucket_name}: {len(conversations)} conversations → {size_mb:.2f} MB")
    
    print(f"\n✅ Done! Files saved to: {output_dir}")
    print(f"   Total size: {total_size:.2f} MB")
    print("\nNext steps:")
    print("1. Upload these files to GitHub (they should be small enough)")
    print("2. Share the raw URLs with Claude")
    print("3. Claude will analyze patterns")


if __name__ == "__main__":
    # Process ChatGPT export
    print("=== ChatGPT Export ===")
    split_conversations_by_time(
        input_file='data-export/chatgpt-export/conversations.json',
        output_dir='data-export/chatgpt-export/split'
    )
    
    print("\n=== Claude Export ===")
    split_conversations_by_time(
        input_file='data-export/claude-export/conversations.json',
        output_dir='data-export/claude-export/split'
    )

