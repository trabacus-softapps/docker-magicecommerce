-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
-- 				FUNCTION:Partywise & Itemwise Sales/Purchase 
-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 

drop type if exists analysis_data cascade;

create type analysis_data as (   
	  party varchar(100), 

	  aquantity numeric(16,2),
	  auntax numeric(16,2),
	  atax numeric(16,2),
	  
	  myquantity numeric(16,2),
	  myuntax numeric(16,2),
	  mytax numeric(16,2),
	  
	  jnquantity numeric(16,2),
	  jnuntax numeric(16,2),
	  jntax numeric(16,2),
	  
	  jlquantity numeric(16,2),
	  jluntax numeric(16,2),
	  jltax numeric(16,2),
	  
	  agquantity numeric(16,2),
	  aguntax numeric(16,2),
	  agtax numeric(16,2),
	  
	  squantity numeric(16,2),
	  suntax numeric(16,2),
	  stax numeric(16,2),
	  
	  oquantity numeric(16,2),
	  ountax numeric(16,2),
	  otax numeric(16,2),
	  
	  nquantity numeric(16,2),
	  nuntax numeric(16,2),
	  ntax numeric(16,2),
	  
	  dquantity numeric(16,2),
	  duntax numeric(16,2),
	  dtax numeric(16,2),
	  
	  jquantity numeric(16,2),
	  juntax numeric(16,2),
	  jtax numeric(16,2),
	  
	  fquantity numeric(16,2),
	  funtax numeric(16,2),
	  ftax numeric(16,2),
	  
	  mquantity numeric(16,2),
	  muntax numeric(16,2),
	  mtax numeric(16,2)
	  );

drop function if exists partywise_sales_purchase(from_date date, to_date date, report_type varchar(20), inv_type varchar(20), compn_id numeric);


CREATE OR REPLACE FUNCTION partywise_sales_purchase(from_date date, to_date date, report_type varchar(20), inv_type varchar(20), compn_id numeric)
RETURNS SETOF analysis_data AS
$BODY$
    DECLARE
       r analysis_data%rowtype;
       i integer :=1;
    BEGIN
    	from_date := to_char((from_date)::date, 'yyyy-mm-dd');
    	to_date := to_char((to_date)::date, 'yyyy-mm-dd');
    	if report_type='annually'THEN
    	DROP TABLE if exists tmp_psales_purchase;
        CREATE TEMP TABLE tmp_psales_purchase
        ( party varchar(100),
	  aquantity numeric(16,2),
	  auntax numeric(16,2),
	  atax numeric(16,2)
        )
	ON COMMIT DROP;
	INSERT INTO tmp_psales_purchase(party, aquantity, auntax, atax)
	(
	/* Anually */
        select 
             x.party  
	   , SUM(x.quantity) as quantity
	   , SUM(x.untax) as untax
           , SUM(x.tax) as tax
			
	from
	(select 
		  rp.name as party	
		, SUM(al.quantity) as quantity
		, SUM(ai.amount_untaxed) as untax
		, SUM(ai.amount_tax) as tax
		
	from account_invoice_line al
		inner join account_invoice ai on ai.id = al.invoice_id 
		inner join res_partner rp on rp.id = ai.partner_id
		WHERE ai.date_invoice between from_date and to_date and ai.state in ('open','paid') and ai.type=inv_type 
		and case when compn_id > 0 then ai.company_id = compn_id else ai.company_id is not null end
		GROUP BY rp.name
		ORDER BY rp.name
	)x

	group by  x.party
	 order by x.party
	);
	
	FOR r IN select * from tmp_psales_purchase LOOP
    	return next r;          
        END LOOP;
	END if;

	/* Quarterlly */

        if report_type='quarterly' THEN
        DROP TABLE if exists tmp_psales_purchase_quart;
        CREATE TEMP TABLE tmp_psales_purchase_quart
        ( party varchar(100),
	  aquantity numeric(16,2),
	  auntax numeric(16,2),
	  atax numeric(16,2),
	  
	  myquantity numeric(16,2),
	  myuntax numeric(16,2),
	  mytax numeric(16,2),
	  
	  jnquantity numeric(16,2),
	  jnuntax numeric(16,2),
	  jntax numeric(16,2),
	  
	  jlquantity numeric(16,2),
	  jluntax numeric(16,2),
	  jltax numeric(16,2)
        )
	ON COMMIT DROP;
	INSERT INTO tmp_psales_purchase_quart(party, aquantity, auntax, atax, myquantity, myuntax, mytax, jnquantity, jnuntax, jntax, jlquantity, jluntax, jltax)
	(
	SELECT 

	
	  y.party
	, SUM(apr_qty+may_qty+jun_qty) as aquarter_qty
	, SUM(apr_untax+may_untax+jun_untax) as aquarter_untax
	, SUM(apr_tax+may_tax+jun_tax) as aquarter_tax
	
	, SUM(jul_qty+aug_qty+sep_qty) as myquarter_qty
	, SUM(jul_untax+aug_untax+sep_untax) as myquarter_untax
	, SUM(jul_tax+aug_tax+sep_tax) as myquarter_tax
	
	, SUM(oct_qty+nov_qty+dec_qty) as jnquarter_qty
	, SUM(oct_untax+nov_untax+dec_untax) as jnquarter_untax
	, SUM(oct_tax+nov_tax+dec_tax) as jnquarter_tax
	
	, SUM(jan_qty+feb_qty+mar_qty) as jlquarter_qty
	, SUM(jan_untax+feb_untax+mar_untax) as jlquarter_untax
	, SUM(jan_tax+feb_tax+mar_tax) as jlquarter_tax
	
	
	FROM
	(SELECT 
		  x.party
		, CASE WHEN x.month like '%APR%' then SUM(quantity) else 0.00 end as apr_qty
		, CASE WHEN x.month like '%APR%' then SUM(untaxed) else 0.00 end as apr_untax
		, CASE WHEN x.month like '%APR%' then SUM(taxed) else 0.00 end as apr_tax
		, CASE WHEN x.month like '%MAY%' then SUM(quantity) else 0.00 end as may_qty
		, CASE WHEN x.month like '%MAY%' then SUM(untaxed) else 0.00 end as may_untax
		, CASE WHEN x.month like '%MAY%' then SUM(taxed) else 0.00 end as may_tax
		, CASE WHEN x.month like '%JUN%' then SUM(quantity) else 0.00 end as jun_qty
		, CASE WHEN x.month like '%JUN%' then SUM(untaxed) else 0.00 end as jun_untax
		, CASE WHEN x.month like '%JUN%' then SUM(taxed) else 0.00 end as jun_tax
		, CASE WHEN x.month like '%JUL%' then SUM(quantity) else 0.00 end as jul_qty
		, CASE WHEN x.month like '%JUL%' then SUM(untaxed) else 0.00 end as jul_untax
		, CASE WHEN x.month like '%JUL%' then SUM(taxed) else 0.00 end as jul_tax
		, CASE WHEN x.month like '%AUG%' then SUM(quantity) else 0.00 end as aug_qty
		, CASE WHEN x.month like '%AUG%' then SUM(untaxed) else 0.00 end as aug_untax
		, CASE WHEN x.month like '%AUG%' then SUM(taxed) else 0.00 end as aug_tax
		, CASE WHEN x.month like '%SEP%' then SUM(quantity) else 0.00 end as sep_qty
		, CASE WHEN x.month like '%SEP%' then SUM(untaxed) else 0.00 end as sep_untax
		, CASE WHEN x.month like '%SEP%' then SUM(taxed) else 0.00 end as sep_tax
		, CASE WHEN x.month like '%OCT%' then SUM(quantity) else 0.00 end as oct_qty
		, CASE WHEN x.month like '%OCT%' then SUM(untaxed) else 0.00 end as oct_untax
		, CASE WHEN x.month like '%OCT%' then SUM(taxed) else 0.00 end as oct_tax
		, CASE WHEN x.month like '%NOV%' then SUM(quantity) else 0.00 end as nov_qty
		, CASE WHEN x.month like '%NOV%' then SUM(untaxed) else 0.00 end as nov_untax
		, CASE WHEN x.month like '%NOV%' then SUM(taxed) else 0.00 end as nov_tax
		, CASE WHEN x.month like '%DEC%' then SUM(quantity) else 0.00 end as dec_qty
		, CASE WHEN x.month like '%DEC%' then SUM(untaxed) else 0.00 end as dec_untax
		, CASE WHEN x.month like '%DEC%' then SUM(taxed) else 0.00 end as dec_tax
		, CASE WHEN x.month like '%JAN%' then SUM(quantity) else 0.00 end as jan_qty
		, CASE WHEN x.month like '%JAN%' then SUM(untaxed) else 0.00 end as jan_untax
		, CASE WHEN x.month like '%JAN%' then SUM(taxed) else 0.00 end as jan_tax
		, CASE WHEN x.month like '%FEB%' then SUM(quantity) else 0.00 end as feb_qty
		, CASE WHEN x.month like '%FEB%' then SUM(untaxed) else 0.00 end as feb_untax
		, CASE WHEN x.month like '%FEB%' then SUM(taxed) else 0.00 end as feb_tax
		, CASE WHEN x.month like '%MAR%' then SUM(quantity) else 0.00 end as mar_qty
		, CASE WHEN x.month like '%MAR%' then SUM(untaxed) else 0.00 end as mar_untax
		, CASE WHEN x.month like '%MAR%' then SUM(taxed) else 0.00 end as mar_tax

	FROM

	(SELECT 	  
		  rp.name as party	
		, SUM(al.quantity) as quantity  
		, SUM(ai.amount_untaxed) as untaxed
		, SUM(ai.amount_tax) as taxed
		, to_char(ai.date_invoice, 'MON-YY') as month
		
		

	FROM account_invoice ai 
	INNER JOIN res_partner rp on rp.id = ai.partner_id
	INNER JOIN account_invoice_line al on al.invoice_id = ai.id
	WHERE ai.date_invoice between from_date and to_date and ai.state in ('open','paid') and ai.type=inv_type 
	and case when compn_id > 0 then ai.company_id = compn_id else ai.company_id is not null end
	GROUP BY party,month
	ORDER BY party
	)x
	
	GROUP BY x.party,x.month
	ORDER BY x.party
	)y
	GROUP BY y.party
	ORDER BY y.party

	);
        
        FOR r IN select * from tmp_psales_purchase_quart LOOP
    	return next r;          
        END LOOP;
	END if;

	/*  Monthly */
	
	if report_type='monthly' THEN	
	DROP TABLE if exists tmp_psales_purchase_month;
        CREATE TEMP TABLE tmp_psales_purchase_month
        ( party varchar(100),
        
	  aquantity numeric(16,2),
	  auntax numeric(16,2),
	  atax numeric(16,2),
	  
	  myquantity numeric(16,2),
	  myuntax numeric(16,2),
	  mytax numeric(16,2),
	  
	  jnquantity numeric(16,2),
	  jnuntax numeric(16,2),
	  jntax numeric(16,2),
	  
	  jlquantity numeric(16,2),
	  jluntax numeric(16,2),
	  jltax numeric(16,2),
	  
	  agquantity numeric(16,2),
	  aguntax numeric(16,2),
	  agtax numeric(16,2),
	  
	  squantity numeric(16,2),
	  suntax numeric(16,2),
	  stax numeric(16,2),
	  
	  oquantity numeric(16,2),
	  ountax numeric(16,2),
	  otax numeric(16,2),
	  
	  nquantity numeric(16,2),
	  nuntax numeric(16,2),
	  ntax numeric(16,2),
	  
	  dquantity numeric(16,2),
	  duntax numeric(16,2),
	  dtax numeric(16,2),
	  
	  jquantity numeric(16,2),
	  juntax numeric(16,2),
	  jtax numeric(16,2),
	  
	  fquantity numeric(16,2),
	  funtax numeric(16,2),
	  ftax numeric(16,2),
	  
	  mquantity numeric(16,2),
	  muntax numeric(16,2),
	  mtax numeric(16,2)
        )
	ON COMMIT DROP;
	INSERT INTO tmp_psales_purchase_month(party, aquantity, auntax, atax, myquantity, myuntax, mytax, jnquantity, jnuntax, jntax, jlquantity, jluntax, jltax, agquantity, aguntax, agtax, 
	squantity, suntax, stax, oquantity, ountax, otax, nquantity, nuntax, ntax, dquantity, duntax, dtax, jquantity, juntax, jtax, fquantity, funtax, ftax, mquantity, muntax, mtax)
	(
	
	SELECT 

	/* Quarterlly */
	  party
	, SUM(apr_qty) as apr_qty
	, SUM(apr_untax) as apr_untax
	, SUM(apr_tax) as apr_tax
	, SUM(may_qty) as may_qty
	, SUM(may_untax) as may_untax
	, SUM(may_tax) as may_tax
	, SUM(jun_qty) as jun_qty
	, SUM(jun_untax) as jun_untax
	, SUM(jun_tax) as jun_tax
	, SUM(jul_qty) as jul_qty
	, SUM(jul_untax) as jul_untax
	, SUM(jul_tax) as jul_tax
	, SUM(aug_qty) as aug_qty
	, SUM(aug_untax) as aug_untax
	, SUM(aug_tax) as aug_tax
	, SUM(sep_qty) as sep_qty
	, SUM(sep_untax) as sep_untax
	, SUM(sep_tax) as sep_tax
	, SUM(oct_qty) as oct_qty
	, SUM(oct_untax) as oct_untax
	, SUM(oct_tax) as oct_tax
	, SUM(nov_qty) as nov_qty
	, SUM(nov_untax) as nov_untax
	, SUM(nov_tax) as nov_tax
	, SUM(dec_qty) as dec_qty
	, SUM(dec_untax) as dec_untax
	, SUM(dec_tax) as dec_tax
	, SUM(jan_qty) as jan_qty
	, SUM(jan_untax) as jan_untax
	, SUM(jan_tax) as jan_tax
	, SUM(feb_qty) as feb_qty
	, SUM(feb_untax) as feb_untax
	, SUM(feb_tax) as feb_tax	
	, SUM(mar_qty) as mar_qty
	, SUM(mar_untax) as mar_untax
	, SUM(mar_tax) as mar_tax	
	FROM
	(SELECT 
		  x.party
		, CASE WHEN x.month like '%APR%' then SUM(quantity) else 0.00 end as apr_qty
		, CASE WHEN x.month like '%APR%' then SUM(untaxed) else 0.00 end as apr_untax
		, CASE WHEN x.month like '%APR%' then SUM(taxed) else 0.00 end as apr_tax
		, CASE WHEN x.month like '%MAY%' then SUM(quantity) else 0.00 end as may_qty
		, CASE WHEN x.month like '%MAY%' then SUM(untaxed) else 0.00 end as may_untax
		, CASE WHEN x.month like '%MAY%' then SUM(taxed) else 0.00 end as may_tax
		, CASE WHEN x.month like '%JUN%' then SUM(quantity) else 0.00 end as jun_qty
		, CASE WHEN x.month like '%JUN%' then SUM(untaxed) else 0.00 end as jun_untax
		, CASE WHEN x.month like '%JUN%' then SUM(taxed) else 0.00 end as jun_tax
		, CASE WHEN x.month like '%JUL%' then SUM(quantity) else 0.00 end as jul_qty
		, CASE WHEN x.month like '%JUL%' then SUM(untaxed) else 0.00 end as jul_untax
		, CASE WHEN x.month like '%JUL%' then SUM(taxed) else 0.00 end as jul_tax
		, CASE WHEN x.month like '%AUG%' then SUM(quantity) else 0.00 end as aug_qty
		, CASE WHEN x.month like '%AUG%' then SUM(untaxed) else 0.00 end as aug_untax
		, CASE WHEN x.month like '%AUG%' then SUM(taxed) else 0.00 end as aug_tax
		, CASE WHEN x.month like '%SEP%' then SUM(quantity) else 0.00 end as sep_qty
		, CASE WHEN x.month like '%SEP%' then SUM(untaxed) else 0.00 end as sep_untax
		, CASE WHEN x.month like '%SEP%' then SUM(taxed) else 0.00 end as sep_tax
		, CASE WHEN x.month like '%OCT%' then SUM(quantity) else 0.00 end as oct_qty
		, CASE WHEN x.month like '%OCT%' then SUM(untaxed) else 0.00 end as oct_untax
		, CASE WHEN x.month like '%OCT%' then SUM(taxed) else 0.00 end as oct_tax
		, CASE WHEN x.month like '%NOV%' then SUM(quantity) else 0.00 end as nov_qty
		, CASE WHEN x.month like '%NOV%' then SUM(untaxed) else 0.00 end as nov_untax
		, CASE WHEN x.month like '%NOV%' then SUM(taxed) else 0.00 end as nov_tax
		, CASE WHEN x.month like '%DEC%' then SUM(quantity) else 0.00 end as dec_qty
		, CASE WHEN x.month like '%DEC%' then SUM(untaxed) else 0.00 end as dec_untax
		, CASE WHEN x.month like '%DEC%' then SUM(taxed) else 0.00 end as dec_tax
		, CASE WHEN x.month like '%JAN%' then SUM(quantity) else 0.00 end as jan_qty
		, CASE WHEN x.month like '%JAN%' then SUM(untaxed) else 0.00 end as jan_untax
		, CASE WHEN x.month like '%JAN%' then SUM(taxed) else 0.00 end as jan_tax
		, CASE WHEN x.month like '%FEB%' then SUM(quantity) else 0.00 end as feb_qty
		, CASE WHEN x.month like '%FEB%' then SUM(untaxed) else 0.00 end as feb_untax
		, CASE WHEN x.month like '%FEB%' then SUM(taxed) else 0.00 end as feb_tax
		, CASE WHEN x.month like '%MAR%' then SUM(quantity) else 0.00 end as mar_qty
		, CASE WHEN x.month like '%MAR%' then SUM(untaxed) else 0.00 end as mar_untax
		, CASE WHEN x.month like '%MAR%' then SUM(taxed) else 0.00 end as mar_tax

	FROM

	(SELECT 	  
		  rp.name as party	
		, SUM(al.quantity) as quantity  
		, SUM(ai.amount_untaxed) as untaxed
		, SUM(ai.amount_tax) as taxed
		, to_char(ai.date_invoice, 'MON-YY') as month
		
		

	FROM account_invoice ai 
	INNER JOIN res_partner rp on rp.id = ai.partner_id
	INNER JOIN account_invoice_line al on al.invoice_id = ai.id
	WHERE ai.date_invoice between from_date and to_date and ai.state in ('open','paid') and ai.type=inv_type 
	and case when compn_id > 0 then ai.company_id = compn_id else ai.company_id is not null end
	GROUP BY party,month
	ORDER BY party
	)x
	
	GROUP BY x.party,x.month
	ORDER BY x.party
	)y
	GROUP BY y.party
	ORDER BY y.party
	);

	FOR r IN select * from tmp_psales_purchase_month LOOP
    	return next r;          
        END LOOP;
	END if;

		
	RETURN;
     END 
  
  $BODY$
LANGUAGE plpgsql VOLATILE;

-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
-- 				FUNCTION:Stock Ledger
-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 


drop type if exists stock_ledger cascade;
create type stock_ledger as (  id integer, 
	 
	  stock_date date,
	  stock_type varchar(10),
	  origin varchar(20),
	  product integer,
	  qty numeric(16,2),
	  tot_qty numeric(16,2)	 
	  );

drop function if exists stock_ledger_func(from_date date, to_date date, prod_id numeric, compn_id numeric, fiscalst_date date);

CREATE OR REPLACE FUNCTION stock_ledger_func(from_date date, to_date date, prod_id numeric, compn_id numeric, fiscalst_date date)

RETURNS SETOF stock_ledger AS
$BODY$
    DECLARE
       r stock_ledger%rowtype;
       prev_qty numeric(16,2) :=0;
       rec record;
       i integer :=1;
       open_bal numeric(16,2) :=0;
       close_bal numeric(16,2) :=0;
    BEGIN
    	from_date := to_char((from_date)::date, 'yyyy-mm-dd');
    	to_date := to_char((to_date)::date, 'yyyy-mm-dd');
    	fiscalst_date := to_char((fiscalst_date)::date, 'yyyy-mm-dd');

    	DROP SEQUENCE if exists do_seq;
	CREATE TEMP sequence do_seq;
    
    	DROP TABLE if exists tmp_stock_ledger;
        CREATE TEMP TABLE tmp_stock_ledger
         
        ( id int,
          stock_date date,
	  stock_type varchar(10),
	  origin varchar(20),
	  product integer,
	  qty numeric(16,2),
	  tot_qty numeric(16,2)	  
        )
	ON COMMIT DROP;

	INSERT INTO tmp_stock_ledger(id,origin,tot_qty)
	(
		select 	nextval('do_seq') as id ,
			'Opening Balance' as origin
			,CASE WHEN sum(a.qty)>0 THEN sum(a.qty) ELSE 0 END as tot_qty
		from
		 (SELECT SUM(sm.product_qty) as qty
			  FROM stock_move sm 
			  INNER JOIN stock_picking s on s.id = sm.picking_id
			  WHERE sm.date::date >= fiscalst_date::date AND sm.date::date < from_date::date 
			  AND sm.product_id = prod_id AND sm.state='done' AND s.type = 'in' AND 
			  CASE WHEN compn_id > 0 THEN sm.company_id = compn_id ELSE sm.company_id > 0 END

			  union all 
			
		 SELECT SUM(-sm.product_qty) as qty 
			FROM stock_move sm 
			INNER JOIN stock_picking s on s.id = sm.picking_id
			WHERE sm.date::date >= fiscalst_date::date AND sm.date::date < from_date::date
			AND sm.product_id = prod_id AND sm.state='done' AND s.type = 'out' AND 
			CASE WHEN compn_id > 0 THEN sm.company_id = compn_id ELSE sm.company_id > 0 END
			)a
	);

	select tot_qty into open_bal from tmp_stock_ledger;
	
	INSERT INTO tmp_stock_ledger(id,stock_date, stock_type, origin, product, qty)
	(
		SELECT 		
		  nextval('do_seq') as id 
		, d.date
		, d.type
		, d.origin
		, d.desc_id
		, sum(d.qty)

		FROM
			(SELECT 
				  sp.date::date
				, sp.type
				, p.name_template as product
				, sm.product_qty as qty
				, sp.origin
				, p.id as desc_id
			FROM stock_picking sp
			INNER JOIN stock_move sm on sm.picking_id = sp.id
			INNER JOIN product_product p on p.id = sm.product_id
			WHERE sp.type='in' and sp.receive BETWEEN from_date AND to_date AND sm.product_id = prod_id AND
			CASE WHEN compn_id > 0 THEN sp.company_id = compn_id ELSE sp.company_id > 0 END

			UNION
				
			SELECT    sp.date::date
				, sp.type
				, rp.name as product
				, sm.product_qty as qty
				, sp.origin
				, rp.id as desc_id
				FROM stock_picking sp
				INNER JOIN stock_move sm on sm.picking_id = sp.id
				INNER JOIN product_product p on p.id = sm.product_id
				INNER JOIN res_partner rp on rp.id =sp.partner_id
				WHERE sp.type='out' and sp.delivery_date BETWEEN from_date AND to_date AND sm.product_id = prod_id AND 
				CASE WHEN compn_id > 0 THEN sp.company_id = compn_id ELSE sp.company_id > 0 END
			)d
			GROUP BY d.desc_id,d.date,d.type,d.origin
			ORDER BY d.date, d.type
	);

	FOR rec IN select * from tmp_stock_ledger LOOP
	    IF rec.id != 1 THEN
	       IF rec.stock_type = 'in' THEN
	          close_bal = (open_bal + rec.qty);
	       ELSE 
		   close_bal = (open_bal - rec.qty);
	       END IF;	
	       
	       update tmp_stock_ledger set tot_qty = close_bal 
	       where id = rec.id;
					 
	       open_bal = close_bal;
	 
	    END IF;
	        
	    
	END LOOP;

	FOR r IN select * from tmp_stock_ledger LOOP
    	return next r;          
        END LOOP;        

	RETURN;
     END 
  
  $BODY$
LANGUAGE plpgsql VOLATILE;