export type Coverage={start:string;end:string};
export type Health={health:string;status:string;project_phase:string;development_data_available:boolean;development_coverage:Coverage;real_money_authorized:boolean};
export type Research={champion:string;experiments_completed:number;evidence:string;backtest_substrate:string;engine_version:string;execution_model_version:string;cost_model_version:string;synthetic_validation:string};
export type Candle={open_time:string;open:number;high:number;low:number;close:number;complete?:boolean};
export type CandlePayload={classification:string;coverage:Coverage;candles:Candle[]};
export async function request<T>(url:string):Promise<T>{const response=await fetch(url);if(!response.ok)throw new Error(`API ${response.status}`);return response.json() as Promise<T>}
