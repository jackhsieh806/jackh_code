class SnapshotArray {
public:
    //index, snap id/val
    //unordered_map<int,unordered_map<int,int>> m;
    unordered_map<int,map<int,int>> m;
    //vector<unordered_map<int,int>> data;
    int snapID = 0;
    SnapshotArray(int length) {
        snapID = 0;
        //data.clear();
        m.clear();
        //for (int i = 0; i < length; ++i) {
         //   m[i] = {{0, 0}};
       //}        
    }
    
    void set(int index, int val) {
        //if (m)
        m[index][snapID] = val;
    }
    
    int snap() {                
        return snapID++;
    }
    
    int get(int index, int snap_id) {

        //if (!m.count(index))
        //    return 0;
        
        auto it = m[index].upper_bound(snap_id);

        if (it == m[index].begin())
            return 0;
        --it;
        
        return it->second;
        
    }    
    int get2(int index, int snap_id) {
        //auto it = m[index].upper_bound(snap_id);
        //--it;
        //while (!m[index].count(snap_id--));
        int id = 0;
        
        for (auto iter = m[index].begin(); iter != m[index].end(); ++iter) {
            if (iter->first > id && iter->first <= snap_id)
                id = iter->first;
        }

        return m[index][id];
        
    }
};

/**
 * Your SnapshotArray object will be instantiated and called as such:
 * SnapshotArray* obj = new SnapshotArray(length);
 * obj->set(index,val);
 * int param_2 = obj->snap();
 * int param_3 = obj->get(index,snap_id);
 */
