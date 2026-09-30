// Only transient failures are retried; validation errors are returned unchanged.
export async function requestApi(url, options={}, onRetry=()=>{}, fetcher=fetch) {
  const delays=[60000,60000];
  for(let attempt=0;attempt<delays.length;attempt++){
    try {
      const response=await fetcher(url,{...options,signal:AbortSignal.timeout(delays[attempt])});
      if(![502,503,504].includes(response.status)||attempt===delays.length-1)return response;
    } catch(error) {
      if(!['TimeoutError','TypeError'].includes(error.name)||attempt===delays.length-1)throw error;
    }
    onRetry();
  }
}
