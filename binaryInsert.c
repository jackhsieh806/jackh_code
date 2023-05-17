    int searchInsert(vector<int>& nums, int target) {
        int sz = nums.size();
        int l = 0,r = sz-1;
        int mid;

        if (sz == 0)
            return -1;

        while (l <= r) {
                mid = (l+r)/2;
                if (nums[mid] < target)
                    l = mid+1;
                else if (nums[mid] > target)
                    r = mid-1;
                else
                    return mid;
        }
        printf("r = %d\r\n",r);
        
        return r+1;

    }
