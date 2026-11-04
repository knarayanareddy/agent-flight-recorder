-- Use within authenticated project-scoped transaction; statement parameters shown as :name.
WITH candidate AS (
 SELECT id FROM core.jobs
 WHERE project_id=:project_id AND state='queued'
 ORDER BY created_at,id FOR UPDATE SKIP LOCKED LIMIT 1
)
UPDATE core.jobs j SET state='leased', attempt=j.attempt+1, fence=j.fence+1,
 lease_until=now()+interval '30 seconds',revision=j.revision+1,updated_at=now()
FROM candidate c WHERE j.id=c.id
RETURNING j.*;
-- Complete only current active fenced attempt. Zero returned rows is stale/invalid, not success.
UPDATE core.jobs SET state=:terminal_state,result_id=:result_id,
 lease_until=NULL,revision=revision+1,updated_at=now()
WHERE id=:job_id AND project_id=:project_id AND fence=:fence
 AND state IN ('leased','running') AND lease_until>now()
 AND :terminal_state IN ('succeeded','failed','timed_out')
RETURNING *;
-- Cancellation race: a job already terminal remains terminal. Cancelled is set only after worker acknowledgement.
UPDATE core.jobs SET state='cancel_requested',revision=revision+1,updated_at=now()
WHERE id=:job_id AND project_id=:project_id AND state IN ('queued','leased','running') RETURNING *;
