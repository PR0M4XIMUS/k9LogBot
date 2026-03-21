#!/usr/bin/env python3
"""Manual cleanup script to remove old records without affecting balance."""

from database import auto_cleanup_old_records, get_transaction_count

def main():
    print("=" * 50)
    print("MANUAL DATABASE CLEANUP")
    print("=" * 50)
    
    # Get count before cleanup
    before = get_transaction_count()
    print(f"\n📊 Records before cleanup: {before}")
    
    # Run cleanup keeping 1 month (current month only)
    print("\n🧹 Running cleanup (keeping current month only)...")
    result = auto_cleanup_old_records(months_to_keep=1)
    
    if result['success']:
        after = get_transaction_count()
        print(f"\n✅ Cleanup successful!")
        print(f"   • Deleted: {result['deleted_count']} records")
        print(f"   • Records older than: {result['cutoff_date']}")
        print(f"   • Records after cleanup: {after}")
        print(f"\n💾 Balance: UNCHANGED (not affected)")
    else:
        print(f"\n❌ Cleanup failed: {result['error']}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
